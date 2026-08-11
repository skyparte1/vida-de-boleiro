from database import connect, init_database

SEASON = 2026

COUNTRY = {
    "code": "NED",
    "name": "Países Baixos",
    "confederation": "UEFA",
}

COMPETITIONS = [
    {"name": "Eredivisie", "type": "league", "tier": 1},
    {"name": "Eerste Divisie", "type": "league", "tier": 2},
    {"name": "KNVB Beker", "type": "cup", "tier": None},
    {"name": "Johan Cruijff Schaal", "type": "supercup", "tier": None},
]

# Ratings provisórios de gameplay (0–100), não oficiais.
EREDIVISIE = {
    "Ajax":                 (99, 89, 100, 97),
    "PSV":                  (99, 95, 97, 98),
    "Feyenoord":            (97, 92, 94, 95),
    "AZ":                   (91, 86, 96, 87),
    "FC Twente":            (88, 85, 89, 84),
    "FC Utrecht":           (87, 84, 86, 83),
    "N.E.C. Nijmegen":      (82, 83, 82, 77),
    "sc Heerenveen":        (84, 80, 88, 77),
    "FC Groningen":         (84, 80, 90, 77),
    "Sparta Rotterdam":     (81, 79, 82, 75),
    "Fortuna Sittard":      (77, 76, 77, 72),
    "Go Ahead Eagles":      (80, 79, 80, 74),
    "PEC Zwolle":           (76, 75, 77, 71),
    "Excelsior Rotterdam":  (73, 74, 81, 68),
    "ADO Den Haag":         (82, 76, 83, 74),
    "SC Cambuur":           (78, 75, 82, 72),
    "Telstar":              (68, 71, 72, 64),
    "Willem II":            (80, 75, 79, 72),
}

EERSTE_DIVISIE = {
    "Almere City FC":       (74, 72, 77, 70),
    "De Graafschap":        (75, 72, 79, 68),
    "FC Den Bosch":         (69, 68, 74, 64),
    "FC Dordrecht":         (68, 69, 80, 63),
    "FC Eindhoven":         (69, 68, 75, 64),
    "FC Emmen":             (74, 72, 77, 70),
    "FC Volendam":          (78, 73, 82, 71),
    "Helmond Sport":        (65, 66, 70, 60),
    "Heracles Almelo":      (80, 74, 80, 74),
    "Jong Ajax":            (70, 69, 99, 72),
    "Jong AZ":              (68, 68, 95, 68),
    "Jong FC Utrecht":      (65, 66, 91, 65),
    "Jong PSV":             (69, 68, 97, 70),
    "MVV Maastricht":       (69, 68, 72, 63),
    "NAC Breda":            (80, 74, 81, 73),
    "RKC Waalwijk":         (77, 72, 77, 70),
    "Roda JC Kerkrade":     (77, 72, 79, 68),
    "TOP Oss":              (63, 65, 68, 58),
    "Vitesse":              (84, 71, 84, 69),
    "VVV-Venlo":            (72, 69, 74, 65),
}

LEAGUES = {
    "Eredivisie": EREDIVISIE,
    "Eerste Divisie": EERSTE_DIVISIE,
}


def get_or_create_country(connection):
    connection.execute(
        """
        INSERT INTO countries (code, name, confederation)
        VALUES (?, ?, ?)
        ON CONFLICT(code) DO UPDATE SET
            name = excluded.name,
            confederation = excluded.confederation
        """,
        (COUNTRY["code"], COUNTRY["name"], COUNTRY["confederation"]),
    )

    return connection.execute(
        "SELECT id FROM countries WHERE code = ?",
        (COUNTRY["code"],),
    ).fetchone()["id"]


def seed_competitions(connection, country_id):
    for competition in COMPETITIONS:
        connection.execute(
            """
            INSERT INTO competitions (country_id, name, type, tier)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(country_id, name) DO UPDATE SET
                type = excluded.type,
                tier = excluded.tier
            """,
            (
                country_id,
                competition["name"],
                competition["type"],
                competition["tier"],
            ),
        )


def get_competition_id(connection, country_id, name):
    row = connection.execute(
        """
        SELECT id
        FROM competitions
        WHERE country_id = ? AND name = ?
        """,
        (country_id, name),
    ).fetchone()

    if row is None:
        raise RuntimeError(f"Competição não encontrada: {name}")

    return row["id"]


def upsert_club(connection, country_id, name, ratings):
    reputation, strength, youth_rating, financial_power = ratings

    connection.execute(
        """
        INSERT INTO clubs (
            country_id,
            name,
            reputation,
            strength,
            youth_rating,
            financial_power
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(country_id, name) DO UPDATE SET
            reputation = excluded.reputation,
            strength = excluded.strength,
            youth_rating = excluded.youth_rating,
            financial_power = excluded.financial_power
        """,
        (
            country_id,
            name,
            reputation,
            strength,
            youth_rating,
            financial_power,
        ),
    )

    return connection.execute(
        """
        SELECT id
        FROM clubs
        WHERE country_id = ? AND name = ?
        """,
        (country_id, name),
    ).fetchone()["id"]


def seed_league_memberships(connection, country_id):
    for competition_name, clubs in LEAGUES.items():
        competition_id = get_competition_id(
            connection,
            country_id,
            competition_name,
        )

        for club_name, ratings in clubs.items():
            club_id = upsert_club(
                connection,
                country_id,
                club_name,
                ratings,
            )

            connection.execute(
                """
                INSERT OR IGNORE INTO club_competition_seasons (
                    club_id,
                    competition_id,
                    season
                )
                VALUES (?, ?, ?)
                """,
                (club_id, competition_id, SEASON),
            )


def validate_seed(connection, country_id):
    expected = {
        "Eredivisie": 18,
        "Eerste Divisie": 20,
    }

    errors = []

    for competition_name, expected_count in expected.items():
        actual = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM club_competition_seasons ccs
            JOIN competitions c
                ON c.id = ccs.competition_id
            WHERE c.country_id = ?
              AND c.name = ?
              AND ccs.season = ?
            """,
            (country_id, competition_name, SEASON),
        ).fetchone()["total"]

        if actual != expected_count:
            errors.append(
                f"{competition_name}: esperado {expected_count}, encontrado {actual}"
            )

    duplicates = sorted(set(EREDIVISIE) & set(EERSTE_DIVISIE))

    if duplicates:
        errors.append(
            "Clubes presentes nas duas divisões: " + ", ".join(duplicates)
        )

    if errors:
        raise RuntimeError(
            "Falha na validação do seed dos Países Baixos:\n- "
            + "\n- ".join(errors)
        )


def print_summary(connection, country_id):
    print(f"\nDados do futebol neerlandês - temporada {SEASON}/27")
    print("-" * 66)

    rows = connection.execute(
        """
        SELECT
            c.name AS competition,
            c.tier,
            COUNT(ccs.club_id) AS clubs
        FROM competitions c
        LEFT JOIN club_competition_seasons ccs
            ON ccs.competition_id = c.id
            AND ccs.season = ?
        WHERE c.country_id = ?
        GROUP BY c.id, c.name, c.tier
        ORDER BY
            CASE WHEN c.tier IS NULL THEN 999 ELSE c.tier END,
            c.name
        """,
        (SEASON, country_id),
    ).fetchall()

    for row in rows:
        tier = row["tier"] if row["tier"] is not None else "-"
        print(
            f"{row['competition']:<40} "
            f"nível={tier!s:<2} clubes={row['clubs']}"
        )

    total = connection.execute(
        "SELECT COUNT(*) AS total FROM clubs WHERE country_id = ?",
        (country_id,),
    ).fetchone()["total"]

    print("-" * 66)
    print(f"Total de clubes neerlandeses cadastrados: {total}")


def main():
    init_database()

    with connect() as connection:
        country_id = get_or_create_country(connection)
        seed_competitions(connection, country_id)
        seed_league_memberships(connection, country_id)
        validate_seed(connection, country_id)
        print_summary(connection, country_id)

    print("\nSeed dos Países Baixos concluído com sucesso.")


if __name__ == "__main__":
    main()
