import datetime
import sqlite3
import os

from flask import jsonify

from config import base_dir, db_path


def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}


def get_song_titles(songNumberList):
    """Return a dict of songNumber to songName for the given numbers."""
    if not songNumberList:
        return {}

    conn = sqlite3.connect(os.path.join(base_dir, "songlist.sqlite"))
    cur = conn.cursor()

    placeholders = ",".join("?" for _ in songNumberList)
    query = (
        f"SELECT songNumber, songName FROM songs WHERE songNumber IN ({placeholders})"
    )

    cur.execute(query, songNumberList)
    rows = cur.fetchall()
    conn.close()

    return {str(number): name for number, name in rows}


def get_songs():
    conn = sqlite3.connect(os.path.join(base_dir, "songlist.sqlite"))
    conn.row_factory = dict_factory
    cur = conn.cursor()
    cur.execute("SELECT songNumber FROM songs ORDER BY songNumber")
    rows = cur.fetchall()
    conn.close()

    song_numbers = [row["songNumber"] for row in rows]
    return jsonify({"songs": song_numbers})


def get_song_info(songNumber):
    song_info = {}
    conn = sqlite3.connect(os.path.join(base_dir, "songlist.sqlite"))
    conn.row_factory = dict_factory
    cur = conn.cursor()
    res = cur.execute(
        "select * from songs where songNumber = ?;", (songNumber,))
    if res:
        song_info = res.fetchone()
    conn.close()
    return jsonify(song_info)



