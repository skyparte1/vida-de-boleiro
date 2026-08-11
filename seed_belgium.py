from database import connect, init_database

SEASON = 2026

COUNTRY = {
    "code": "BEL",
    "name": "Bélgica",
    "confederation": "UEFA",
}

COMPETITIONS = [
    {"name": "Jupiler Pro League", "type": "league", "tier": 1},
    {"name": "Challenger Pro League", "type": "league", "tier": 2},
    {"name": "Croky Cup", "type": "cup", "tier": None},
    {"name": "Belgian Supercup", "type": "supercup", "tier": None},
]

# Ratings provisórios de gameplay (0–100), não oficiais.
JUPILER_PRO_LEAGUE = {
    "Royale Union Saint-Gilloise": (93, 91, 89, 88),
    "Club Brugge":                 (96, 92, 92, 95),
    "Sporting Charleroi":          (84, 81, 80, 78),
    "KAA Gent":                    (88, 84, 87, 84),
    "RSC Anderlecht":              (97, 87, 94, 94),
    "Royal Antwerp FC":            (92, 86, 86, 90),
    "SV Zulte Waregem":            (78, 77, 78, 73),
    "Cercle Brugge":               (82, 80, 85, 78),
    "Standard de Liège":           (93, 82, 88, 87),
    "Lommel SK":                   (72, 74, 83, 76),
    "STVV":                        (81, 78, 83, 75),
    "SK Beveren":                  (76, 75, 78, 72),
    "KRC Genk":                    (92, 88, 96, 90),
    "RAAL La Louvière":            (70, 73, 76, 67),
    "OH Leuven":                   (80, 79, 86, 82),
    "KV Mechelen":                 (83, 80, 81, 78),
    "KV Kortrijk":                 (77, 75, 76, 72),
    "KVC Westerlo":                (79, 78, 82, 76),
}

CHALLENGER_PRO_LEAGUE = {
    "Club NXT":                    (69, 68, 95, 72),
    "FCV Dender EH":               (73, 71, 75, 69),
    "Jong Genk":                   (68, 68, 96, 70),
    "Jong KAA Gent":               (66, 66, 91, 67),
    "K. Beerschot VA":             (80, 72, 78, 75),
    "K. Lierse S.K.":              (78, 71, 76, 70),
    "KAS Eupen":                   (76, 72, 80, 71),
    "KSC Lokeren":                 (74, 70, 75, 68),
    "Patro Eisden Maasmechelen":   (67, 69, 72, 63),
    "RFC Liège":                   (74, 70, 74, 66),
    "RFC Seraing":                 (72, 69, 74, 66),
    "Royal Excelsior Virton":      (66, 67, 70, 61),
    "Royal Francs Borains":        (64, 66, 69, 60),
    "RSCA Futures":                (69, 68, 96, 72),
    "Sporting Hasselt":            (63, 65, 69, 59),
}

LEAGUES = {
    "Jupiler Pro League": JUPILER_PRO_LEAGUE,
    "Challenger Pro League": CHALLENGER_PRO_LEAGUE,
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
        "Jupiler Pro League": 18,
        "Challenger Pro League": 15,
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

    duplicates = sorted(
        set(JUPILER_PRO_LEAGUE) & set(CHALLENGER_PRO_LEAGUE)
    )

    if duplicates:
        errors.append(
            "Clubes presentes nas duas divisões: " + ", ".join(duplicates)
        )

    if errors:
        raise RuntimeError(
            "Falha na validação do seed da Bélgica:\n- "
            + "\n- ".join(errors)
        )


def print_summary(connection, country_id):
    print(f"\nDados do futebol belga - temporada {SEASON}/27")
    print("-" * 68)

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
            f"{row['competition']:<42} "
            f"nível={tier!s:<2} clubes={row['clubs']}"
        )

    total = connection.execute(
        "SELECT COUNT(*) AS total FROM clubs WHERE country_id = ?",
        (country_id,),
    ).fetchone()["total"]

    print("-" * 68)
    print(f"Total de clubes belgas cadastrados: {total}")


def main():
    init_database()

    with connect() as connection:
        country_id = get_or_create_country(connection)
        seed_competitions(connection, country_id)
        seed_league_memberships(connection, country_id)
        validate_seed(connection, country_id)
        print_summary(connection, country_id)

    print("\nSeed da Bélgica concluído com sucesso.")


if __name__ == "__main__":
    main()
