from database import connect, init_database

SEASON = 2026

COUNTRY = {
    "code": "ARG",
    "name": "Argentina",
    "confederation": "CONMEBOL",
}

COMPETITIONS = [
    {"name": "Liga Profesional", "type": "league", "tier": 1},
    {"name": "Primera Nacional", "type": "league", "tier": 2},
    {"name": "Copa Argentina", "type": "cup", "tier": None},
    {"name": "Supercopa Argentina", "type": "supercup", "tier": None},
]

# Ratings provisórios de gameplay (0–100), não oficiais.
LIGA_PROFESIONAL = {
    "Aldosivi":                 (72, 71, 72, 68),
    "Argentinos Juniors":       (88, 84, 93, 82),
    "Atlético Tucumán":         (80, 78, 79, 74),
    "Banfield":                 (82, 78, 87, 75),
    "Barracas Central":         (73, 74, 71, 70),
    "Belgrano":                 (84, 81, 82, 78),
    "Boca Juniors":             (100, 93, 95, 99),
    "Central Córdoba":          (77, 76, 74, 72),
    "Defensa y Justicia":       (84, 82, 91, 80),
    "Deportivo Riestra":        (72, 74, 70, 68),
    "Estudiantes de Río Cuarto":(70, 72, 76, 66),
    "Estudiantes LP":           (91, 88, 91, 86),
    "Gimnasia LP":              (85, 79, 86, 78),
    "Gimnasia de Mendoza":      (71, 73, 76, 67),
    "Huracán":                  (87, 82, 84, 80),
    "Independiente":            (97, 87, 91, 91),
    "Independiente Rivadavia":  (75, 77, 75, 71),
    "Instituto":                (78, 78, 80, 73),
    "Lanús":                    (90, 85, 91, 84),
    "Newell's Old Boys":        (90, 81, 90, 82),
    "Platense":                 (80, 80, 79, 74),
    "Racing Club":              (98, 91, 93, 94),
    "River Plate":              (100, 95, 98, 100),
    "Rosario Central":          (93, 87, 91, 86),
    "San Lorenzo":              (97, 84, 90, 88),
    "Sarmiento":                (75, 74, 74, 69),
    "Talleres":                 (88, 85, 90, 84),
    "Tigre":                    (81, 80, 84, 76),
    "Unión":                    (81, 80, 82, 76),
    "Vélez Sarsfield":          (94, 88, 97, 88),
}

PRIMERA_NACIONAL = {
    "Acassuso":                 (61, 63, 66, 57),
    "Agropecuario":             (66, 67, 70, 62),
    "All Boys":                 (76, 69, 74, 66),
    "Almagro":                  (72, 67, 71, 63),
    "Almirante Brown":          (73, 69, 71, 65),
    "Atlanta":                  (78, 70, 76, 68),
    "Atlético de Rafaela":      (77, 71, 79, 69),
    "Central Norte":            (68, 67, 70, 62),
    "Chacarita Juniors":        (82, 72, 79, 71),
    "Chaco For Ever":           (70, 68, 71, 64),
    "Ciudad de Bolívar":        (62, 66, 69, 59),
    "Colegiales":               (64, 66, 69, 60),
    "Colón":                    (85, 75, 81, 75),
    "Defensores de Belgrano":   (70, 69, 72, 64),
    "Deportivo Madryn":         (69, 71, 73, 65),
    "Deportivo Maipú":          (67, 69, 72, 63),
    "Deportivo Morón":          (77, 72, 75, 68),
    "Estudiantes (BA)":         (70, 69, 74, 65),
    "Ferrocarril Midland":      (62, 65, 68, 58),
    "Ferro Carril Oeste":       (84, 73, 82, 72),
    "Gimnasia y Esgrima (J)":   (72, 70, 75, 66),
    "Gimnasia y Tiro":          (70, 69, 72, 64),
    "Godoy Cruz":               (88, 78, 84, 82),
    "Güemes":                   (65, 67, 69, 60),
    "Los Andes":                (76, 70, 75, 66),
    "Mitre (SdE)":              (67, 68, 70, 62),
    "Nueva Chicago":            (80, 71, 78, 68),
    "Patronato":                (78, 71, 75, 69),
    "Quilmes":                  (84, 73, 82, 73),
    "Racing (Córdoba)":         (71, 70, 74, 65),
    "San Martín (SJ)":          (80, 73, 77, 70),
    "San Martín (Tucumán)":     (82, 74, 80, 71),
    "San Miguel":               (66, 67, 70, 61),
    "San Telmo":                (65, 66, 69, 60),
    "Temperley":                (77, 71, 74, 68),
    "Tristán Suárez":           (66, 67, 70, 61),
}

LEAGUES = {
    "Liga Profesional": LIGA_PROFESIONAL,
    "Primera Nacional": PRIMERA_NACIONAL,
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
        "Liga Profesional": 30,
        "Primera Nacional": 36,
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

    duplicates = sorted(set(LIGA_PROFESIONAL) & set(PRIMERA_NACIONAL))
    if duplicates:
        errors.append(
            "Clubes presentes nas duas divisões: " + ", ".join(duplicates)
        )

    if errors:
        raise RuntimeError(
            "Falha na validação do seed da Argentina:\n- "
            + "\n- ".join(errors)
        )


def print_summary(connection, country_id):
    print(f"\nDados do futebol argentino - temporada {SEASON}")
    print("-" * 66)

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
            f"{row['competition']:<40} "
            f"nível={tier!s:<2} clubes={row['clubs']}"
        )

    total = connection.execute(
        "SELECT COUNT(*) AS total FROM clubs WHERE country_id = ?",
        (country_id,),
    ).fetchone()["total"]

    print("-" * 66)
    print(f"Total de clubes argentinos cadastrados: {total}")


def main():
    init_database()

    with connect() as connection:
        country_id = get_or_create_country(connection)
        seed_competitions(connection, country_id)
        seed_league_memberships(connection, country_id)
        validate_seed(connection, country_id)
        print_summary(connection, country_id)

    print("\nSeed da Argentina concluído com sucesso.")


if __name__ == "__main__":
    main()
