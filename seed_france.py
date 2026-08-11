from database import connect, init_database

SEASON = 2026

COUNTRY = {
    "code": "FRA",
    "name": "França",
    "confederation": "UEFA",
}

COMPETITIONS = [
    {"name": "Ligue 1", "type": "league", "tier": 1},
    {"name": "Ligue 2", "type": "league", "tier": 2},
    {"name": "Coupe de France", "type": "cup", "tier": None},
    {"name": "Trophée des Champions", "type": "supercup", "tier": None},
]

# Ratings provisórios de gameplay (0–100), não oficiais.
LIGUE_1 = {
    "Paris Saint-Germain":       (100, 98, 98, 100),
    "Olympique de Marseille":    (96, 91, 88, 94),
    "Olympique Lyonnais":        (95, 87, 92, 89),
    "AS Monaco":                 (93, 89, 94, 92),
    "LOSC Lille":                (90, 87, 91, 87),
    "RC Lens":                   (89, 88, 86, 84),
    "Stade Rennais FC":          (88, 85, 92, 86),
    "OGC Nice":                  (87, 84, 88, 86),
    "RC Strasbourg Alsace":      (84, 83, 90, 84),
    "Toulouse FC":               (81, 80, 85, 78),
    "Stade Brestois 29":         (81, 80, 78, 75),
    "AJ Auxerre":                (79, 77, 82, 73),
    "FC Lorient":                (79, 77, 81, 74),
    "Angers SCO":                (76, 75, 76, 70),
    "Le Havre AC":               (76, 74, 78, 70),
    "Paris FC":                  (80, 78, 84, 87),
    "ESTAC Troyes":              (74, 74, 78, 70),
    "Le Mans FC":                (70, 72, 74, 65),
}

LIGUE_2 = {
    "FC Nantes":                 (88, 78, 88, 83),
    "FC Metz":                   (82, 76, 82, 77),
    "AS Saint-Étienne":          (91, 78, 90, 82),
    "Montpellier Hérault SC":    (86, 75, 84, 78),
    "Stade de Reims":            (84, 76, 84, 77),
    "EA Guingamp":               (77, 73, 78, 70),
    "Grenoble Foot 38":          (69, 69, 72, 64),
    "USL Dunkerque":             (68, 70, 72, 63),
    "Clermont Foot 63":          (75, 71, 76, 69),
    "Pau FC":                    (67, 68, 70, 62),
    "Rodez AF":                  (66, 68, 69, 61),
    "Stade Lavallois":           (68, 68, 69, 62),
    "AS Nancy Lorraine":         (75, 69, 75, 66),
    "US Boulogne CO":            (64, 66, 67, 59),
    "Dijon FCO":                 (73, 68, 73, 66),
    "FC Sochaux-Montbéliard":    (78, 69, 79, 68),
    "Red Star FC":               (70, 68, 72, 65),
    "FC Annecy":                 (65, 67, 70, 60),
}

LEAGUES = {
    "Ligue 1": LIGUE_1,
    "Ligue 2": LIGUE_2,
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
        "Ligue 1": 18,
        "Ligue 2": 18,
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

    duplicates = sorted(set(LIGUE_1) & set(LIGUE_2))

    if duplicates:
        errors.append(
            "Clubes presentes nas duas divisões: " + ", ".join(duplicates)
        )

    if errors:
        raise RuntimeError(
            "Falha na validação do seed da França:\n- "
            + "\n- ".join(errors)
        )


def print_summary(connection, country_id):
    print(f"\nDados do futebol francês - temporada {SEASON}/27")
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
    print(f"Total de clubes franceses cadastrados: {total}")


def main():
    init_database()

    with connect() as connection:
        country_id = get_or_create_country(connection)
        seed_competitions(connection, country_id)
        seed_league_memberships(connection, country_id)
        validate_seed(connection, country_id)
        print_summary(connection, country_id)

    print("\nSeed da França concluído com sucesso.")


if __name__ == "__main__":
    main()
