from database import connect, init_database

SEASON = 2026

COUNTRY = {
    "code": "ESP",
    "name": "Espanha",
    "confederation": "UEFA",
}

COMPETITIONS = [
    {"name": "LaLiga", "type": "league", "tier": 1},
    {"name": "LaLiga 2", "type": "league", "tier": 2},
    {"name": "Copa del Rey", "type": "cup", "tier": None},
    {"name": "Supercopa de España", "type": "cup", "tier": None},
]

# Ratings provisórios de gameplay (0-100), não oficiais.
LALIGA = {
    "Athletic Club":              (90, 86, 91, 86),
    "Atlético de Madrid":         (96, 93, 88, 96),
    "CA Osasuna":                 (79, 78, 76, 75),
    "Celta":                      (82, 80, 85, 78),
    "Deportivo Alavés":           (75, 74, 72, 70),
    "Elche CF":                   (73, 72, 75, 68),
    "FC Barcelona":               (100, 97, 100, 100),
    "Getafe CF":                  (78, 77, 69, 74),
    "Levante UD":                 (75, 73, 76, 69),
    "Málaga CF":                  (78, 74, 80, 73),
    "R. Racing Club":             (76, 73, 80, 70),
    "Rayo Vallecano":             (78, 78, 73, 72),
    "RC Deportivo":               (82, 75, 85, 76),
    "RCD Espanyol de Barcelona":  (82, 78, 80, 78),
    "Real Betis":                 (87, 85, 82, 84),
    "Real Madrid":                (100, 98, 96, 100),
    "Real Sociedad":              (89, 84, 92, 86),
    "Sevilla FC":                 (91, 80, 83, 86),
    "Valencia CF":                (91, 82, 88, 83),
    "Villarreal CF":              (88, 86, 86, 86),
}

LALIGA_2 = {
    "AD Ceuta FC":          (62, 64, 65, 58),
    "Albacete BP":          (68, 68, 70, 64),
    "Burgos CF":            (67, 68, 66, 63),
    "Cádiz CF":             (76, 71, 72, 70),
    "CD Castellón":         (67, 70, 69, 63),
    "CD Eldense":           (63, 65, 67, 59),
    "CD Leganés":           (74, 71, 72, 70),
    "CD Tenerife":          (73, 68, 75, 67),
    "CE Sabadell":          (65, 65, 69, 60),
    "Celta Fortuna":        (61, 64, 84, 58),
    "Córdoba CF":           (70, 69, 72, 65),
    "FC Andorra":           (64, 66, 74, 62),
    "Girona FC":            (80, 74, 83, 76),
    "Granada CF":           (76, 72, 77, 72),
    "R. Sociedad B":        (62, 65, 88, 59),
    "RCD Mallorca":         (80, 74, 74, 76),
    "Real Oviedo":          (75, 71, 75, 70),
    "Real Sporting":        (76, 71, 79, 69),
    "Real Valladolid CF":   (79, 72, 80, 74),
    "SD Eibar":             (75, 72, 73, 70),
    "UD Almería":           (78, 74, 78, 76),
    "UD Las Palmas":        (78, 73, 82, 73),
}

LEAGUES = {
    "LaLiga": LALIGA,
    "LaLiga 2": LALIGA_2,
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
            country_id, name, reputation, strength,
            youth_rating, financial_power,
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
    expected = {"LaLiga": 20, "LaLiga 2": 22}
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

    duplicates = sorted(set(LALIGA) & set(LALIGA_2))
    if duplicates:
        errors.append(
            "Clubes presentes nas duas divisões: " + ", ".join(duplicates)
        )

    if errors:
        raise RuntimeError(
            "Falha na validação do seed da Espanha:\n- "
            + "\n- ".join(errors)
        )


def print_summary(connection, country_id):
    print(f"\nDados do futebol espanhol - temporada {SEASON}/27")
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
        print(f"{row['competition']:<36} nível={tier!s:<2} clubes={row['clubs']}")

    total = connection.execute(
        "SELECT COUNT(*) AS total FROM clubs WHERE country_id = ?",
        (country_id,),
    ).fetchone()["total"]

    print("-" * 62)
    print(f"Total de clubes espanhóis cadastrados: {total}")


def main():
    init_database()
    with connect() as connection:
        country_id = get_or_create_country(connection)
        seed_competitions(connection, country_id)
        seed_league_memberships(connection, country_id)
        validate_seed(connection, country_id)
        print_summary(connection, country_id)

    print("\nSeed da Espanha concluído com sucesso.")


if __name__ == "__main__":
    main()
