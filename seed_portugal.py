from database import connect, init_database

SEASON = 2026

COUNTRY = {
    "code": "POR",
    "name": "Portugal",
    "confederation": "UEFA",
}

COMPETITIONS = [
    {"name": "Liga Portugal Betclic", "type": "league", "tier": 1},
    {"name": "Liga Portugal 2 Meu Super", "type": "league", "tier": 2},
    {"name": "Taça de Portugal", "type": "cup", "tier": None},
    {"name": "Allianz Cup", "type": "cup", "tier": None},
    {"name": "Supertaça Cândido de Oliveira", "type": "supercup", "tier": None},
]

# Ratings provisórios de gameplay (0–100), não oficiais.
LIGA_PORTUGAL = {
    "FC Porto":               (99, 93, 95, 98),
    "Sporting CP":            (98, 93, 96, 97),
    "SL Benfica":             (99, 94, 98, 99),
    "SC Braga":               (93, 88, 91, 90),
    "Vitória SC":             (87, 83, 87, 82),
    "FC Famalicão":           (82, 80, 88, 80),
    "Gil Vicente FC":         (78, 77, 81, 73),
    "Moreirense FC":          (76, 76, 76, 70),
    "FC Arouca":              (75, 75, 78, 70),
    "Estoril Praia":          (78, 76, 84, 74),
    "FC Alverca":             (70, 72, 76, 67),
    "Rio Ave FC":             (78, 76, 81, 74),
    "FC Santa Clara":         (78, 77, 78, 74),
    "CD Nacional":            (77, 74, 76, 70),
    "Estrela da Amadora":     (74, 74, 80, 70),
    "Casa Pia AC":            (74, 74, 77, 70),
    "Marítimo":               (81, 77, 82, 76),
    "Académico de Viseu":     (71, 72, 76, 67),
}

LIGA_PORTUGAL_2 = {
    "Académica":              (77, 70, 78, 68),
    "AFS":                    (73, 70, 72, 72),
    "Amarante FC":            (65, 66, 70, 60),
    "SL Benfica B":           (70, 70, 92, 72),
    "GD Chaves":              (75, 72, 75, 70),
    "SC Farense":             (77, 72, 76, 72),
    "CD Feirense":            (69, 68, 72, 64),
    "FC Felgueiras 1932":     (65, 67, 70, 61),
    "Leixões SC":             (72, 69, 75, 66),
    "Lusitânia Lourosa":      (63, 65, 69, 59),
    "FC Penafiel":            (69, 68, 71, 63),
    "Portimonense":           (75, 71, 74, 70),
    "FC Porto B":             (70, 70, 90, 72),
    "Sporting CP B":          (69, 69, 91, 71),
    "CD Tondela":             (74, 71, 75, 69),
    "SCU Torreense":          (69, 70, 73, 65),
    "UD Leiria":              (74, 70, 76, 68),
    "FC Vizela":              (72, 70, 74, 67),
}

LEAGUES = {
    "Liga Portugal Betclic": LIGA_PORTUGAL,
    "Liga Portugal 2 Meu Super": LIGA_PORTUGAL_2,
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
        "Liga Portugal Betclic": 18,
        "Liga Portugal 2 Meu Super": 18,
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

    duplicates = sorted(set(LIGA_PORTUGAL) & set(LIGA_PORTUGAL_2))

    if duplicates:
        errors.append(
            "Clubes presentes nas duas divisões: " + ", ".join(duplicates)
        )

    if errors:
        raise RuntimeError(
            "Falha na validação do seed de Portugal:\n- "
            + "\n- ".join(errors)
        )


def print_summary(connection, country_id):
    print(f"\nDados do futebol português - temporada {SEASON}/27")
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
    print(f"Total de clubes portugueses cadastrados: {total}")


def main():
    init_database()

    with connect() as connection:
        country_id = get_or_create_country(connection)
        seed_competitions(connection, country_id)
        seed_league_memberships(connection, country_id)
        validate_seed(connection, country_id)
        print_summary(connection, country_id)

    print("\nSeed de Portugal concluído com sucesso.")


if __name__ == "__main__":
    main()
