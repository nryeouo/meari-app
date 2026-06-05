import os
import sqlite3
from config import base_dir
from utils.common import dict_factory


DB_PATH = os.path.join(base_dir, "songlist.sqlite")


def fetch_all(query, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = dict_factory
        return conn.execute(query, params).fetchall()


def fetch_one(query, params=()):
    rows = fetch_all(query, params)
    return rows[0] if rows else None


def get_songs():
    rows = fetch_all("SELECT songNumber FROM songs ORDER BY songNumber")
    return {"songs": [row["songNumber"] for row in rows]}


def get_song_info(song_number):
    return fetch_one("SELECT * FROM songs WHERE songNumber = ?", (song_number,)) or {}


def get_song_titles(song_numbers):
    if not song_numbers:
        return {}

    placeholders = ",".join("?" for _ in song_numbers)
    rows = fetch_all(
        f"SELECT songNumber, songName FROM songs WHERE songNumber IN ({placeholders})",
        song_numbers,
    )
    return {str(row["songNumber"]): row["songName"] for row in rows}
