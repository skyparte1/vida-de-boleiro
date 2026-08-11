from database import connect, init_database

SEASON = 2026

COUNTRY = {
    "code": "ENG",
    "name": "Inglaterra",
    "confederation": "UEFA",
}

COMPETITIONS = [
    {"name": "Premier League", "type": "league", "tier": 1},
    {"name": "EFL Championship", "type": "league", "tier": 2},
    {"name": "FA Cup", "type": "cup", "tier": None},
    {"name": "EFL Cup", "type": "cup", "tier": None},
]

# Ratings de gameplay provisórios (0–100).
# Não são ratings oficiais; servem para dar hierarquia inicial ao simulador.
# Você pode refiná-los depois sem alterar a estrutura do banco.
PREMIER_LEAGUE = {
    "Arsenal":               (96, 94, 91, 96),
    "Aston Villa":           (86, 84, 80, 86),
    "Bournemouth":           (74, 76, 68, 72),
    "Brentford":             (76, 76, 72, 76),
    "Brighton & Hove Albion":(80, 79, 86, 79),
    "Chelsea":               (94, 91, 91, 97),
    "Coventry City":         (68, 69, 69, 66),
    "Crystal Palace":        (81, 80, 75, 77),
    "Everton":               (86, 78, 77, 84),
    "Fulham":                (79, 77, 71, 79),
    "Hull City":             (65, 67, 68, 64),
    "Ipswich Town":          (70, 70, 73, 68),
    "Leeds United":          (84, 79, 84, 82),
    "Liverpool":             (97, 94, 90, 97),
    "Manchester City":       (98, 95, 92, 100),
    "Manchester United":     (98, 84, 86, 100),
    "Newcastle United":      (89, 86, 82, 92),
    "Nottingham Forest":     (80, 80, 72, 79),
    "Sunderland":            (78, 76, 77, 75),
    "Tottenham Hotspur":     (92, 83, 88, 95),
}

CHAMPIONSHIP = {
    "Birmingham City":          (72, 71, 72, 73),
    "Blackburn Rovers":         (72, 69, 77, 67),
    "Bolton Wanderers":         (70, 68, 72, 67),
    "Bristol City":             (68, 68, 72, 66),
    "Burnley":                  (77, 74, 74, 76),
    "Cardiff City":             (72, 69, 72, 68),
    "Charlton Athletic":        (71, 68, 71, 66),
    "Derby County":             (76, 69, 74, 69),
    "Lincoln City":             (62, 65, 68, 59),
    "Middlesbrough":            (73, 73, 78, 72),
    "Millwall":                 (70, 70, 67, 66),
    "Norwich City":             (74, 72, 79, 72),
    "Portsmouth":               (73, 68, 72, 68),
    "Preston North End":        (66, 67, 68, 62),
    "Queens Park Rangers":      (73, 68, 74, 71),
    "Sheffield United":         (78, 73, 75, 76),
    "Southampton":              (80, 74, 86, 79),
    "Stoke City":               (75, 69, 70, 74),
    "Swansea City":             (72, 69, 78, 67),
    "Watford":                  (75, 70, 76, 73),
    "West Bromwich Albion":     (76, 71, 74, 72),
    "West Ham United":          (88, 78, 82, 90),
    "Wolverhampton Wanderers":  (83, 76, 80, 83),
    "Wrexham":                  (69, 70, 68, 74),
}

LEAGUES = {
    "Premier League": (1, PREMIER_LEAGUE),
    "EFL Championship": (2, CHAMPIONSHIP),
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
    for competition_name, (_tier, clubs) in LEAGUES.items():
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
        "Premier League": 20,
        "EFL Championship": 24,
    }

    errors = []

    for competition_name, expected_count in expected.items():
        row = connection.execute(
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
        ).fetchone()

        actual = row["total"]

        if actual != expected_count:
            errors.append(
                f"{competition_name}: esperado {expected_count}, encontrado {actual}"
            )

    premier = set(PREMIER_LEAGUE)
    championship = set(CHAMPIONSHIP)
    duplicates = sorted(premier & championship)

    if duplicates:
        errors.append(
            "Clubes presentes nas duas divisões: " + ", ".join(duplicates)
        )

    if errors:
        raise RuntimeError(
            "Falha na validação do seed da Inglaterra:\n- "
            + "\n- ".join(errors)
        )


def print_summary(connection, country_id):
    print(f"\nDados do futebol inglês - temporada {SEASON}/27")
    print("-" * 62)

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
            f"{row['competition']:<36} "
            f"nível={tier!s:<2} clubes={row['clubs']}"
        )

    total = connection.execute(
        "SELECT COUNT(*) AS total FROM clubs WHERE country_id = ?",
        (country_id,),
    ).fetchone()["total"]

    print("-" * 62)
    print(f"Total de clubes ingleses cadastrados: {total}")


def main():
    init_database()

    with connect() as connection:
        country_id = get_or_create_country(connection)
        seed_competitions(connection, country_id)
        seed_league_memberships(connection, country_id)
        validate_seed(connection, country_id)
        print_summary(connection, country_id)

    print("\nSeed da Inglaterra concluído com sucesso.")


if __name__ == "__main__":
    main()
