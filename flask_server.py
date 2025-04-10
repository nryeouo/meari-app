from about_app import *
from flask import Flask, abort, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import math
import os
import requests
import sqlite3
import subprocess

from config import base_dir, video_files_dir, resv_api_url
VIDEO_DIR = os.path.join(video_files_dir, "video")
PROCESSED_DIR = os.path.join(video_files_dir, "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)

about = aboutApp()
version_info_dict = {"name": about.name,
                     "version": about.version, "owner": about.owner}

app = Flask(__name__, static_folder="static", static_url_path="/static")
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
    songs = [f for f in os.listdir(VIDEO_DIR) if f.endswith(".mp4")]
    return jsonify({"songs": songs})



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
    start = request.args.get("start", type=float)
    duration = request.args.get("duration", default=8.0, type=float)
    pitch = request.args.get("pitch", default=0, type=int)

    if start is None:
        conn = sqlite3.connect(os.path.join(base_dir, "songlist.sqlite"))
        cur = conn.cursor()
        cur.execute(
            "SELECT vocalStartTime FROM songs WHERE songNumber=?", (songNumber,))
        row = cur.fetchone()
        conn.close()
        if row is None:
            return abort(404)
        start = row[0]

    input_path = os.path.join(VIDEO_DIR, f"{songNumber}.mp4")
    output_path = f"/tmp/preview_{songNumber}_{start}_{pitch}.mp3"

    semitones = pitch
    rubberband_pitch = round(math.pow(2, semitones / 12), 5)

    filter_chain = f"atrim=start={start}:duration={duration},asetpts=PTS-STARTPTS,afade=t=in:st=0:d=1,afade=t=out:st={duration-1}:d=1"
    if pitch != 0:
        filter_chain += f",rubberband=pitch={rubberband_pitch}"

    command = [
        "ffmpeg", "-loglevel", "error", "-y", "-i", input_path,
        "-vn", "-af", filter_chain,
        "-ar", "48000", "-ac", "2", "-b:a", "192k",
        output_path
    ]
    subprocess.run(command, check=True)

    return send_file(output_path, mimetype="audio/mpeg")


@app.route("/convert", methods=["POST"])
def convert_video():
    data = request.json
    song_number = data.get("song_number")
    pitch = int(data.get("pitch", 0))

    input_file = os.path.join(VIDEO_DIR, f"{song_number}.mp4")
    output_file = os.path.join(PROCESSED_DIR, f"{song_number}_p{pitch}.mp4")

    if not os.path.exists(input_file):
        return jsonify({"error": "File not found"}), 404

    if pitch == 0:
        output_file = input_file
    else:
        pitch_factor = 2 ** (pitch / 12)
        speed_correction = 1 / pitch_factor

        ffmpeg_cmd = [
            "ffmpeg", "-n", "-loglevel", "error", "-i", input_file,
            "-filter_complex", f"[0:a]rubberband=pitch={(2**(pitch/12)):.2f}:formant=preserved[a]",
            "-map", "0:v", "-map", "[a]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            output_file
        ]

        ffmpeg_cmd1 = [
            "ffmpeg", "-n", "-loglevel", "error", "-i", input_file,
            "-filter_complex", f"[0:a]asetrate=48000*{pitch_factor},atempo={speed_correction},aresample=48000[a]",
            "-map", "0:v", "-map", "[a]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            output_file
        ]
        subprocess.run(ffmpeg_cmd, check=True)

    return jsonify({"processed_file": os.path.basename(output_file)})


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
    bgm_dir = os.path.join(video_files_dir, "bgm")
    bgm_files = [f for f in os.listdir(bgm_dir) if f.endswith(".mp3")]
    return jsonify(bgm_files)


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


@app.route("/bgm/<filename>", methods=["GET"])
def get_bgm(filename):
    bgm_file_dir = os.path.join(video_files_dir, "bgm")
    bgm_file_path = os.path.join(bgm_file_dir, filename)
    if os.path.exists(bgm_file_path):
        return send_from_directory(bgm_file_dir, filename)
    else:
        return abort(404)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5556, debug=True)
