import json
import sqlite3
from pathlib import Path


DATABASE_PATH = Path(__file__).with_name("vida_de_boleiro.db")


def connect():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    with connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL
            )
            """
        )


def save_player(player, player_id=None):
    init_database()
    payload = json.dumps(player, ensure_ascii=False)
    with connect() as connection:
        if player_id is None:
            cursor = connection.execute("INSERT INTO players (data) VALUES (?)", (payload,))
            return cursor.lastrowid
        connection.execute("UPDATE players SET data = ? WHERE id = ?", (payload, player_id))
    return player_id


def get_player(player_id):
    init_database()
    with connect() as connection:
        row = connection.execute("SELECT data FROM players WHERE id = ?", (player_id,)).fetchone()
    return json.loads(row["data"]) if row else None
