from about_app import *
from flask import Flask, abort, request, redirect, jsonify, send_file, send_from_directory
from flask_cors import CORS
from google.cloud import storage
import datetime
import math
import os
import requests
import sqlite3
import subprocess
import tempfile


# from config import base_dir, video_files_dir, resv_api_url
from config import base_dir, resv_api_url
# VIDEO_DIR = os.path.join(video_files_dir, "video")
# PROCESSED_DIR = os.path.join(video_files_dir, "processed")
# os.makedirs(PROCESSED_DIR, exist_ok=True)

about = aboutApp()
version_info_dict = {"name": about.name,
                     "version": about.version, "owner": about.owner}

app = Flask(__name__, static_folder="static", static_url_path="/static")
client = storage.Client()
bucket = client.bucket("meari-video")
CORS(app)


def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}


def get_song_titles(songNumberList):
    conn = sqlite3.connect(os.path.join(base_dir, "songlist.sqlite"))
    cur = conn.cursor()

    placeholders = ",".join("?" for _ in songNumberList)
    q = f"SELECT songNumber, songName FROM songs WHERE songNumber IN ({placeholders})"

    cur.execute(q, songNumberList)
    rows = cur.fetchall()
    conn.close()

    return {str(number): name for number, name in rows}


DB_PATH = os.path.join(base_dir, "history.sqlite")

def init_db():
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time INTEGER,
                songNumber TEXT,
                pitch INTEGER,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

init_db()


def write_history(time, songNumber, pitch, status):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("insert into history (time, songNumber, pitch, status) values (?, ?, ?, ?)", (time, songNumber, pitch, status))
    conn.commit()
    conn.close()
    return "ok"


@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/about")
def version_info():
    return jsonify(version_info_dict)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.static_folder, "favicon.ico")


@app.route("/songs", methods=["GET"])
def get_songs():
    conn = sqlite3.connect(os.path.join(base_dir, "songlist.sqlite"))
    conn.row_factory = dict_factory
    cur = conn.cursor()
    cur.execute("SELECT songNumber FROM songs ORDER BY songNumber")
    rows = cur.fetchall()
    conn.close()

    song_numbers = [row["songNumber"] for row in rows]
    return jsonify({"songs": song_numbers})


@app.route("/next_reserved_song")
def next_reserved_song():
    try:
        res = requests.get(resv_api_url, timeout=3)
        res.raise_for_status()
        return jsonify(res.json())
    except requests.RequestException as e:
        print("予約システムへの接続エラー:", e)
        return jsonify({"has_next": False})


@app.route("/song_info/<songNumber>", methods=["GET"])
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


@app.route("/preview/<songNumber>")
def preview_song(songNumber):
    pitch = int(request.args.get("pitch", 0))

    # GCS上のMP3を指定
    preview_blob = storage.Client().bucket("meari-video").blob(f"preview/{songNumber}.mp3")

    if not preview_blob.exists():
        return jsonify({"error": "preview mp3 not found"}), 404

    # pitch = 0 → 署名付きURLでリダイレクト
    if pitch == 0:
        url = preview_blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(minutes=15),
            method="GET"
        )
        return redirect(url)

    # pitch ≠ 0 → mp3を一時DLしてrubberbandで音程変更
    with tempfile.NamedTemporaryFile(suffix=".mp3") as temp_input, \
         tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_output:

        preview_blob.download_to_filename(temp_input.name)

        cmd = [
            "ffmpeg", "-y",
            "-loglevel", "error",
            "-i", temp_input.name,
            "-af", f"rubberband=pitch={2 ** (pitch / 12):.5f}",
            "-acodec", "libmp3lame",
            temp_output.name
        ]

        try:
            subprocess.run(cmd, check=True)
            return send_file(temp_output.name, mimetype="audio/mpeg")
        except subprocess.CalledProcessError:
            return jsonify({"error": "ffmpeg pitch change failed"}), 500


@app.route("/convert", methods=["POST"])
def convert_video():
    data = request.json
    song_number = data.get("song_number")
    pitch = int(data.get("pitch", 0))

    input_blob = storage.Client().bucket("meari-video").blob(f"{song_number}.mp4")
    if not input_blob.exists():
        return jsonify({"error": "video not found"}), 404

    with tempfile.NamedTemporaryFile(suffix=".mp4") as temp_input, \
         tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_output:

        input_blob.download_to_filename(temp_input.name)

        if pitch == 0:
            # pitch変更なし → 元のファイルの署名付きURLを返す
            url = input_blob.generate_signed_url(
                version="v4",
                expiration=datetime.timedelta(minutes=15),
                method="GET"
            )
            return jsonify({"processed_file": url})

        cmd = [
            "ffmpeg", "-y",
            "-loglevel", "error",
            "-i", temp_input.name,
            "-af", f"rubberband=pitch={2 ** (pitch / 12):.5f}",
            "-c:v", "copy",
            temp_output.name
        ]
        subprocess.run(cmd, check=True)

        # 一時的にGCSにアップロードして署名URLを返す
        output_blob = storage.Client().bucket("meari-temp").blob(f"temp/{song_number}_{pitch:+d}.mp4")
        output_blob.upload_from_filename(temp_output.name)

        url = output_blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(minutes=15),
            method="GET"
        )
        return jsonify({"processed_file": url})


@app.route("/control/<controlname>", methods=["POST"])
def control_handler(controlname):
    valid_statuses = {"playStarted", "playEnded", "playAborted"}
    if controlname in valid_statuses:
        return handle_play_event(controlname)
    return jsonify({"error": "Unknown control name"}), 400


def handle_play_event(status):
    data = request.json
    time = data.get("time")
    songNumber = data.get("songNumber")
    pitch = data.get("pitch")
    write_history(time, songNumber, pitch, status)
    return jsonify({"status": "ok"})


@app.route("/history")
def read_history():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
    cur = conn.cursor()
    cur.execute("SELECT songNumber, time FROM history WHERE status = 'playEnded' ORDER BY time DESC LIMIT 10")
    rows = cur.fetchall()
    conn.close()

    song_numbers = [row["songNumber"] for row in rows]
    title_dict = get_song_titles(song_numbers)

    return jsonify([
        {
            "songNumber": str(row["songNumber"]),
            "songTitle": title_dict.get(str(row["songNumber"]), "제목없음"),
            "time": row["time"]
        }
        for row in rows
    ])


@app.route("/bgm_list")
def bgm_list():
    bucket = storage.Client().bucket("meari-video")
    blobs = list(bucket.list_blobs(prefix="bgm/"))
    bgm_files = [blob.name.replace("bgm/", "") for blob in blobs if blob.name.endswith(".mp3")]
    return jsonify(bgm_files)

"""
@app.route("/video/<filename>", methods=["GET"])
def get_video(filename):
    # 変換後の動画があればそれを提供、なければ元の動画を提供
    processed_path = os.path.join(PROCESSED_DIR, filename)
    original_path = os.path.join(VIDEO_DIR, filename)

    if os.path.exists(processed_path):
        return send_from_directory(PROCESSED_DIR, filename)
    elif os.path.exists(original_path):
        return send_from_directory(VIDEO_DIR, filename)
    else:
        return abort(404)
"""

@app.route("/video/<filename>")
def get_signed_video_url(filename):
    blob = bucket.blob(filename)
    if not blob.exists():
        return jsonify({"error": "File not found"}), 404

    url = blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(minutes=15),
        method="GET"
    )
    return jsonify({"url": url})


@app.route("/bgm/<filename>")
def get_bgm(filename):
    blob = storage.Client().bucket("meari-video").blob(f"bgm/{filename}")
    if not blob.exists():
        return jsonify({"error": "not found"}), 404
    url = blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(minutes=15),
        method="GET"
    )
    return redirect(url)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
