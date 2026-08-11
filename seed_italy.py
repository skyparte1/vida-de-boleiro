from database import connect, init_database

SEASON = 2026

COUNTRY = {
    "code": "ITA",
    "name": "Itália",
    "confederation": "UEFA",
}

COMPETITIONS = [
    {"name": "Serie A", "type": "league", "tier": 1},
    {"name": "Serie B", "type": "league", "tier": 2},
    {"name": "Coppa Italia", "type": "cup", "tier": None},
    {"name": "Supercoppa Italiana", "type": "cup", "tier": None},
]

# Ratings provisórios de gameplay (0–100), não oficiais.
SERIE_A = {
    "AC Milan":       (98, 92, 89, 98),
    "Atalanta":       (90, 88, 88, 87),
    "Bologna":        (84, 83, 82, 80),
    "Cagliari":       (77, 75, 75, 72),
    "Como":           (82, 83, 80, 92),
    "Fiorentina":     (88, 84, 84, 84),
    "Frosinone":      (73, 72, 75, 68),
    "Genoa":          (82, 78, 79, 76),
    "Inter":          (99, 95, 91, 98),
    "Juventus":       (99, 92, 94, 99),
    "Lazio":          (91, 85, 83, 88),
    "Lecce":          (75, 74, 78, 69),
    "Monza":          (76, 75, 78, 78),
    "Napoli":         (96, 93, 88, 95),
    "Parma":          (82, 78, 86, 78),
    "Roma":           (95, 89, 88, 92),
    "Sassuolo":       (82, 80, 84, 80),
    "Torino":         (86, 81, 82, 82),
    "Udinese":        (82, 79, 84, 79),
    "Venezia":        (76, 75, 78, 72),
}

SERIE_B = {
    "Arezzo":          (64, 65, 67, 60),
    "Ascoli":          (72, 68, 72, 66),
    "Avellino":        (70, 69, 70, 65),
    "Benevento":       (71, 69, 72, 67),
    "Carrarese":       (64, 66, 67, 60),
    "Catanzaro":       (69, 70, 72, 66),
    "Cesena":          (72, 71, 78, 68),
    "Cremonese":       (76, 73, 74, 73),
    "Empoli":          (78, 73, 84, 73),
    "Hellas Verona":   (82, 74, 80, 76),
    "Juve Stabia":     (66, 68, 68, 62),
    "L.R. Vicenza":    (69, 68, 72, 65),
    "Mantova":         (65, 67, 69, 61),
    "Modena":          (70, 70, 73, 66),
    "Padova":          (69, 68, 72, 65),
    "Palermo":         (79, 74, 77, 78),
    "Pisa":            (76, 72, 76, 71),
    "Sampdoria":       (86, 72, 78, 77),
    "Südtirol":        (65, 67, 67, 61),
    "Virtus Entella":  (64, 66, 68, 60),
}

LEAGUES = {
    "Serie A": SERIE_A,
    "Serie B": SERIE_B,
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
        "SELECT id FROM competitions WHERE country_id = ? AND name = ?",
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
            country_id, name, reputation, strength,
            youth_rating, financial_power
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
        "SELECT id FROM clubs WHERE country_id = ? AND name = ?",
        (country_id, name),
    ).fetchone()["id"]


def seed_league_memberships(connection, country_id):
    for competition_name, clubs in LEAGUES.items():
        competition_id = get_competition_id(
            connection, country_id, competition_name
        )

        for club_name, ratings in clubs.items():
            club_id = upsert_club(
                connection, country_id, club_name, ratings
            )

            connection.execute(
                """
                INSERT OR IGNORE INTO club_competition_seasons (
                    club_id, competition_id, season
                )
                VALUES (?, ?, ?)
                """,
                (club_id, competition_id, SEASON),
            )


def validate_seed(connection, country_id):
    expected = {
        "Serie A": 20,
        "Serie B": 20,
    }

    errors = []

    for competition_name, expected_count in expected.items():
        actual = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM club_competition_seasons ccs
            JOIN competitions c ON c.id = ccs.competition_id
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

    duplicates = sorted(set(SERIE_A) & set(SERIE_B))

    if duplicates:
        errors.append(
            "Clubes presentes nas duas divisões: " + ", ".join(duplicates)
        )

    if errors:
        raise RuntimeError(
            "Falha na validação do seed da Itália:\n- "
            + "\n- ".join(errors)
        )


def print_summary(connection, country_id):
    print(f"\nDados do futebol italiano - temporada {SEASON}/27")
    print("-" * 62)

    rows = connection.execute(
        """
        SELECT c.name AS competition, c.tier, COUNT(ccs.club_id) AS clubs
        FROM competitions c
        LEFT JOIN club_competition_seasons ccs
          ON ccs.competition_id = c.id AND ccs.season = ?
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
            f"{row['competition']:<36} "
            f"nível={tier!s:<2} clubes={row['clubs']}"
        )

    total = connection.execute(
        "SELECT COUNT(*) AS total FROM clubs WHERE country_id = ?",
        (country_id,),
    ).fetchone()["total"]

    print("-" * 62)
    print(f"Total de clubes italianos cadastrados: {total}")


def main():
    init_database()

    with connect() as connection:
        country_id = get_or_create_country(connection)
        seed_competitions(connection, country_id)
        seed_league_memberships(connection, country_id)
        validate_seed(connection, country_id)
        print_summary(connection, country_id)

    print("\nSeed da Itália concluído com sucesso.")


if __name__ == "__main__":
    main()
