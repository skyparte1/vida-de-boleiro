from database import connect, init_database

SEASON = 2026
COUNTRY = {"code": "BRA", "name": "Brasil", "confederation": "CONMEBOL"}
COMPETITIONS = [
    {"name": "Campeonato Brasileiro Série A", "type": "league", "tier": 1},
    {"name": "Campeonato Brasileiro Série B", "type": "league", "tier": 2},
    {"name": "Campeonato Brasileiro Série C", "type": "league", "tier": 3},
    {"name": "Campeonato Brasileiro Série D", "type": "league", "tier": 4},
    {"name": "Copa do Brasil", "type": "cup", "tier": None},
    {"name": "Supercopa Rei", "type": "supercup", "tier": None},
]
TIER_RATINGS = {
    1: {"reputation": 80, "strength": 80, "youth_rating": 75, "financial_power": 80},
    2: {"reputation": 65, "strength": 65, "youth_rating": 65, "financial_power": 65},
    3: {"reputation": 55, "strength": 55, "youth_rating": 55, "financial_power": 55},
    4: {"reputation": 45, "strength": 45, "youth_rating": 45, "financial_power": 45},
}

SERIE_A = [
    "Flamengo", "Palmeiras", "Cruzeiro", "Mirassol", "Fluminense", "Bahia",
    "Botafogo", "São Paulo", "Red Bull Bragantino", "Corinthians", "Grêmio",
    "Vasco da Gama", "Atlético-MG", "Santos", "Vitória", "Internacional",
    "Coritiba", "Athletico-PR", "Chapecoense", "Remo",
]

SERIE_B = [
    "América-MG", "Athletic", "Atlético-GO", "Avaí", "Botafogo-SP", "Ceará",
    "CRB", "Criciúma", "Cuiabá", "Fortaleza", "Goiás", "Juventude", "Londrina",
    "Náutico", "Novorizontino", "Operário-PR", "Ponte Preta", "São Bernardo",
    "Sport", "Vila Nova",
]

SERIE_C = [
    "Inter de Limeira", "Floresta", "Ituano", "Anápolis", "Brusque", "Caxias",
    "Confiança", "Amazonas", "Maranhão", "Guarani", "Volta Redonda", "Paysandu",
    "Maringá", "Ferroviária", "Ypiranga-RS", "Figueirense", "Santa Cruz",
    "Itabaiana", "Botafogo-PB", "Barra-SC",
]

SERIE_D = [
    "ABC", "ABECAT", "Água Santa", "Águia de Marabá", "Altos", "América-RJ",
    "América-RN", "Aparecidense", "Araguaína", "ASA", "Atlético-CE",
    "Atlético de Alagoinhas", "Azuriz", "Betim", "Brasil de Pelotas", "Brasiliense",
    "Blumenau", "Capital-DF", "Ceilândia", "Central", "Cianorte", "CRAC", "CSA",
    "CSE", "Decisão", "Democrata GV", "FC Cascavel", "Ferroviário", "Fluminense-PI",
    "Galvez", "Gama", "GAS", "Porto Velho", "Goiatuba", "Guaporé", "Guarany de Bagé",
    "Humaitá", "IAPE", "Iguatu", "Imperatriz", "Independência", "Inhumas", "Ivinhema",
    "Jacuipense", "Joinville", "Juazeirense", "Lagarto", "Laguna", "Luverdense",
    "Maguary", "Manauara", "Manaus", "Maracanã", "Marcílio Dias", "Maricá", "Mixto",
    "Moto Club", "Monte Roraima", "Nacional-AM", "Noroeste", "Nova Iguaçu", "Operário-MS",
    "Operário VG", "Oratório", "Parnahyba", "Piauí", "Porto-BA", "Portuguesa-SP",
    "Pouso Alegre", "Primavera-MT", "Real Noroeste", "Retrô", "Rio Branco-ES", "Vitória-ES",
    "Sampaio Corrêa-MA", "Sampaio Corrêa-RJ", "Santa Catarina", "São José-RS",
    "São Joseense", "São Luiz", "São Raimundo-RR", "Sergipe", "Serra Branca", "Sousa",
    "Tirol", "Trem", "Tocantinópolis", "Tombense", "Treze", "Tuna Luso", "Uberlândia",
    "União Rondonópolis", "Velo Clube", "XV de Piracicaba", "Madureira", "Portuguesa-RJ",
]

LEAGUES = {
    1: ("Campeonato Brasileiro Série A", SERIE_A),
    2: ("Campeonato Brasileiro Série B", SERIE_B),
    3: ("Campeonato Brasileiro Série C", SERIE_C),
    4: ("Campeonato Brasileiro Série D", SERIE_D),
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
        "SELECT id FROM countries WHERE code = ?", (COUNTRY["code"],)
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
            (country_id, competition["name"], competition["type"], competition["tier"]),
        )


def competition_id(connection, country_id, name):
    row = connection.execute(
        "SELECT id FROM competitions WHERE country_id = ? AND name = ?",
        (country_id, name),
    ).fetchone()
    if row is None:
        raise RuntimeError(f"Competição não encontrada: {name}")
    return row["id"]


def upsert_club(connection, country_id, name, tier):
    ratings = TIER_RATINGS[tier]
    connection.execute(
        """
        INSERT INTO clubs (
            country_id, name, reputation, strength, youth_rating, financial_power
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(country_id, name) DO UPDATE SET
            reputation = excluded.reputation,
            strength = excluded.strength,
            youth_rating = excluded.youth_rating,
            financial_power = excluded.financial_power
        """,
        (
            country_id, name, ratings["reputation"], ratings["strength"],
            ratings["youth_rating"], ratings["financial_power"],
        ),
    )
    return connection.execute(
        "SELECT id FROM clubs WHERE country_id = ? AND name = ?",
        (country_id, name),
    ).fetchone()["id"]


def seed_league_memberships(connection, country_id):
    for tier, (competition_name, clubs) in LEAGUES.items():
        comp_id = competition_id(connection, country_id, competition_name)
        for club_name in clubs:
            club_id = upsert_club(connection, country_id, club_name, tier)
            connection.execute(
                """
                INSERT OR IGNORE INTO club_competition_seasons (
                    club_id, competition_id, season
                ) VALUES (?, ?, ?)
                """,
                (club_id, comp_id, SEASON),
            )


def validate_seed(connection, country_id):
    expected = {
        "Campeonato Brasileiro Série A": 20,
        "Campeonato Brasileiro Série B": 20,
        "Campeonato Brasileiro Série C": 20,
        "Campeonato Brasileiro Série D": 96,
    }
    errors = []
    for competition_name, expected_count in expected.items():
        actual = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM club_competition_seasons ccs
            JOIN competitions c ON c.id = ccs.competition_id
            WHERE c.country_id = ? AND c.name = ? AND ccs.season = ?
            """,
            (country_id, competition_name, SEASON),
        ).fetchone()["total"]
        if actual != expected_count:
            errors.append(f"{competition_name}: esperado {expected_count}, encontrado {actual}")
    if errors:
        raise RuntimeError("Falha na validação do seed:\n- " + "\n- ".join(errors))


def print_summary(connection, country_id):
    print(f"\nDados do futebol brasileiro - temporada {SEASON}")
    print("-" * 56)
    rows = connection.execute(
        """
        SELECT c.name AS competition, c.tier, COUNT(ccs.club_id) AS clubs
        FROM competitions c
        LEFT JOIN club_competition_seasons ccs
            ON ccs.competition_id = c.id AND ccs.season = ?
        WHERE c.country_id = ?
        GROUP BY c.id, c.name, c.tier
        ORDER BY CASE WHEN c.tier IS NULL THEN 999 ELSE c.tier END, c.name
        """,
        (SEASON, country_id),
    ).fetchall()
    for row in rows:
        tier = row["tier"] if row["tier"] is not None else "-"
        print(f"{row['competition']:<38} nível={tier!s:<2} clubes={row['clubs']}")
    total = connection.execute(
        "SELECT COUNT(*) AS total FROM clubs WHERE country_id = ?", (country_id,)
    ).fetchone()["total"]
    print("-" * 56)
    print(f"Total de clubes brasileiros cadastrados: {total}")


def main():
    init_database()
    with connect() as connection:
        country_id = get_or_create_country(connection)
        seed_competitions(connection, country_id)
        seed_league_memberships(connection, country_id)
        validate_seed(connection, country_id)
        print_summary(connection, country_id)
    print("\nSeed concluído com sucesso.")


if __name__ == "__main__":
    main()
