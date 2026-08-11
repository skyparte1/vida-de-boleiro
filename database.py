import json
import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).with_name("vida_de_boleiro.db")


def connect():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_database():
    with connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS countries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT UNIQUE NOT NULL,
                confederation TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS competitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                tier INTEGER,

                FOREIGN KEY (country_id)
                    REFERENCES countries(id),

                UNIQUE(country_id, name)
            );

            CREATE TABLE IF NOT EXISTS clubs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country_id INTEGER NOT NULL,
                name TEXT NOT NULL,

                logo TEXT,

                reputation INTEGER NOT NULL DEFAULT 50,
                strength INTEGER NOT NULL DEFAULT 50,
                youth_rating INTEGER NOT NULL DEFAULT 50,
                financial_power INTEGER NOT NULL DEFAULT 50,

                FOREIGN KEY (country_id) REFERENCES countries(id),

                UNIQUE(country_id, name)
            );

            CREATE TABLE IF NOT EXISTS club_competition_seasons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                club_id INTEGER NOT NULL,
                competition_id INTEGER NOT NULL,
                season INTEGER NOT NULL,

                FOREIGN KEY (club_id)
                    REFERENCES clubs(id),

                FOREIGN KEY (competition_id)
                    REFERENCES competitions(id),

                UNIQUE(club_id, competition_id, season)
            );
            """
        )


def save_player(player, player_id=None):
    init_database()

    payload = json.dumps(
        player,
        ensure_ascii=False
    )

    with connect() as connection:
        if player_id is None:
            cursor = connection.execute(
                "INSERT INTO players (data) VALUES (?)",
                (payload,)
            )

            return cursor.lastrowid

        connection.execute(
            "UPDATE players SET data = ? WHERE id = ?",
            (payload, player_id)
        )

        return player_id


def get_player(player_id):
    init_database()

    with connect() as connection:
        row = connection.execute(
            "SELECT data FROM players WHERE id = ?",
            (player_id,)
        ).fetchone()

        return json.loads(row["data"]) if row else None


CLUB_FIELDS = """
    clubs.id, clubs.country_id, clubs.name, clubs.reputation, clubs.strength,
    clubs.youth_rating, clubs.financial_power, clubs.city, clubs.state,
    clubs.founded_year, clubs.logo, countries.code AS country_code,
    countries.name AS country, countries.confederation AS confederation
"""

COMPETITION_FIELDS = """
    competitions.id, competitions.country_id, competitions.name,
    competitions.type, competitions.tier, countries.code AS country_code,
    countries.name AS country, countries.confederation AS confederation
"""


def _one(query, parameters=()):
    connection = connect()
    try:
        row = connection.execute(query, parameters).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def _many(query, parameters=()):
    connection = connect()
    try:
        return [dict(row) for row in connection.execute(query, parameters).fetchall()]
    finally:
        connection.close()


def get_country_by_name(name):
    """Obtém um país permanente pelo nome armazenado no SQLite."""
    return _one("SELECT id, code, name, confederation FROM countries WHERE name = ?", (name,))


def get_club(club_id):
    """Obtém um clube e seus dados permanentes pelo ID estável do SQLite."""
    return _one(
        f"SELECT {CLUB_FIELDS} FROM clubs JOIN countries ON countries.id = clubs.country_id WHERE clubs.id = ?",
        (club_id,),
    )


def get_club_by_name(name, country_code=None):
    """Obtém um clube por nome, restringindo o país quando informado."""
    query = f"SELECT {CLUB_FIELDS} FROM clubs JOIN countries ON countries.id = clubs.country_id WHERE clubs.name = ?"
    parameters = [name]
    if country_code:
        query += " AND countries.code = ?"
        parameters.append(country_code)
    return _one(query + " ORDER BY clubs.id LIMIT 1", parameters)


def get_clubs_by_country(country_code):
    """Lista clubes cadastrados para um país, com dados de exibição completos."""
    return _many(
        f"SELECT {CLUB_FIELDS} FROM clubs JOIN countries ON countries.id = clubs.country_id "
        "WHERE countries.code = ? ORDER BY clubs.reputation ASC, clubs.name ASC",
        (country_code,),
    )


def get_clubs_by_competition(competition_id, season=2026):
    """Lista os clubes participantes de uma competição em uma temporada."""
    return _many(
        f"SELECT {CLUB_FIELDS} FROM club_competition_seasons "
        "JOIN clubs ON clubs.id = club_competition_seasons.club_id "
        "JOIN countries ON countries.id = clubs.country_id "
        "WHERE club_competition_seasons.competition_id = ? AND club_competition_seasons.season = ? "
        "ORDER BY clubs.reputation DESC, clubs.name ASC",
        (competition_id, season),
    )


def get_clubs_with_competition(season=2026):
    """Lista clubes reais que possuem uma competição válida na temporada.

    A consulta evita montar o universo de transferências a partir de listas
    estáticas ou de uma consulta por clube.
    """
    return _many(
        f"SELECT {CLUB_FIELDS}, "
        "competitions.id AS competition_id, competitions.name AS competition_name, "
        "competitions.type AS competition_type, competitions.tier AS competition_tier "
        "FROM club_competition_seasons "
        "JOIN clubs ON clubs.id = club_competition_seasons.club_id "
        "JOIN countries ON countries.id = clubs.country_id "
        "JOIN competitions ON competitions.id = club_competition_seasons.competition_id "
        "WHERE club_competition_seasons.season = ? "
        "ORDER BY clubs.id",
        (season,),
    )


def get_club_competition(club_id, season=2026):
    """Obtém a competição de um clube em uma temporada específica."""
    return _one(
        f"SELECT {COMPETITION_FIELDS} FROM club_competition_seasons "
        "JOIN competitions ON competitions.id = club_competition_seasons.competition_id "
        "JOIN countries ON countries.id = competitions.country_id "
        "WHERE club_competition_seasons.club_id = ? AND club_competition_seasons.season = ? "
        "ORDER BY competitions.tier, competitions.id LIMIT 1",
        (club_id, season),
    )


def get_current_competition_for_club(club_id, season=2026):
    """Nome explícito para o consumidor de jogo da competição atual do clube."""
    return get_club_competition(club_id, season)


def get_competition(competition_id):
    """Obtém uma competição e seu país pelo ID estável do SQLite."""
    return _one(
        f"SELECT {COMPETITION_FIELDS} FROM competitions JOIN countries ON countries.id = competitions.country_id "
        "WHERE competitions.id = ?",
        (competition_id,),
    )


def get_competitions_by_country(country_code):
    """Lista as competições permanentes de um país."""
    return _many(
        f"SELECT {COMPETITION_FIELDS} FROM competitions JOIN countries ON countries.id = competitions.country_id "
        "WHERE countries.code = ? ORDER BY competitions.tier, competitions.name",
        (country_code,),
    )
