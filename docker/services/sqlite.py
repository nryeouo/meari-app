import os
import sqlite3
from utils.common import base_dir, dict_factory

def get_songs():
    conn = sqlite3.connect(os.path.join(base_dir, "songlist.sqlite"))
    conn.row_factory = dict_factory
    cur = conn.cursor()
    cur.execute("SELECT songNumber FROM songs ORDER BY songNumber")
    rows = cur.fetchall()
    conn.close()

    song_numbers = [row["songNumber"] for row in rows]
    return {"songs": song_numbers}
