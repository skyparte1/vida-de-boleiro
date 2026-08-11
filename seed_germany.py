from database import connect, init_database

SEASON = 2026

COUNTRY = {
    "code": "GER",
    "name": "Alemanha",
    "confederation": "UEFA",
}

COMPETITIONS = [
    {"name": "Bundesliga", "type": "league", "tier": 1},
    {"name": "2. Bundesliga", "type": "league", "tier": 2},
    {"name": "DFB-Pokal", "type": "cup", "tier": None},
    {"name": "DFL-Supercup", "type": "supercup", "tier": None},
]

# Ratings provisórios de gameplay (0–100), não oficiais.
BUNDESLIGA = {
    "FC Bayern München":          (100, 98, 96, 100),
    "Borussia Dortmund":          (98, 93, 94, 98),
    "RB Leipzig":                 (91, 89, 93, 94),
    "VfB Stuttgart":              (89, 88, 90, 87),
    "TSG Hoffenheim":             (83, 82, 85, 83),
    "Bayer 04 Leverkusen":        (95, 92, 94, 95),
    "Sport-Club Freiburg":        (86, 84, 88, 82),
    "Eintracht Frankfurt":        (90, 87, 89, 88),
    "FC Augsburg":                (78, 77, 78, 74),
    "1. FSV Mainz 05":            (82, 80, 82, 77),
    "1. FC Union Berlin":         (82, 79, 78, 76),
    "Borussia Mönchengladbach":   (89, 82, 86, 84),
    "Hamburger SV":               (88, 80, 84, 82),
    "1. FC Köln":                 (87, 80, 86, 81),
    "SV Werder Bremen":           (89, 82, 84, 82),
    "FC Schalke 04":              (91, 79, 86, 82),
    "SV Elversberg":              (69, 73, 75, 65),
    "SC Paderborn 07":            (73, 75, 78, 68),
}

BUNDESLIGA_2 = {
    "VfL Wolfsburg":              (89, 80, 86, 90),
    "1. FC Heidenheim 1846":      (77, 76, 76, 72),
    "FC St. Pauli":               (82, 77, 82, 75),
    "Hannover 96":                (80, 74, 78, 72),
    "SV Darmstadt 98":            (75, 72, 74, 68),
    "1. FC Kaiserslautern":       (83, 73, 78, 70),
    "Hertha BSC":                 (87, 75, 86, 78),
    "1. FC Nürnberg":             (84, 72, 83, 70),
    "VfL Bochum 1848":            (80, 73, 77, 72),
    "Karlsruher SC":              (75, 71, 76, 67),
    "SG Dynamo Dresden":          (78, 70, 75, 66),
    "Holstein Kiel":              (74, 71, 77, 67),
    "DSC Arminia Bielefeld":      (76, 70, 76, 66),
    "1. FC Magdeburg":            (71, 70, 74, 64),
    "Eintracht Braunschweig":     (73, 68, 71, 64),
    "SpVgg Greuther Fürth":       (72, 69, 73, 65),
    "VfL Osnabrück":              (69, 67, 70, 62),
    "FC Energie Cottbus":         (71, 68, 71, 63),
}

LEAGUES = {
    "Bundesliga": BUNDESLIGA,
    "2. Bundesliga": BUNDESLIGA_2,
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
        "Bundesliga": 18,
        "2. Bundesliga": 18,
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

    duplicates = sorted(set(BUNDESLIGA) & set(BUNDESLIGA_2))

    if duplicates:
        errors.append(
            "Clubes presentes nas duas divisões: " + ", ".join(duplicates)
        )

    if errors:
        raise RuntimeError(
            "Falha na validação do seed da Alemanha:\n- "
            + "\n- ".join(errors)
        )


def print_summary(connection, country_id):
    print(f"\nDados do futebol alemão - temporada {SEASON}/27")
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
    print(f"Total de clubes alemães cadastrados: {total}")


def main():
    init_database()

    with connect() as connection:
        country_id = get_or_create_country(connection)
        seed_competitions(connection, country_id)
        seed_league_memberships(connection, country_id)
        validate_seed(connection, country_id)
        print_summary(connection, country_id)

    print("\nSeed da Alemanha concluído com sucesso.")


if __name__ == "__main__":
    main()
