from flask import Flask, abort, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import math
import os
import sqlite3
import subprocess

from config import base_dir, video_files_dir
VIDEO_DIR = os.path.join(video_files_dir, "video")
PROCESSED_DIR = os.path.join(video_files_dir, "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)

from about_app import *
about = aboutApp()
version_info_dict = {"name": about.name, "version": about.version, "owner": about.owner}

app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app)


def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}


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
        cur.execute("SELECT vocalStartTime FROM songs WHERE songNumber=?", (songNumber,))
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
        ffmpeg_cmd = [
            "ffmpeg", "-i", input_file,
            "-filter_complex", f"[0:a]rubberband=pitch={(2**(pitch/12)):.2f}[a]",
            "-map", "0:v", "-map", "[a]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            output_file
        ]
        subprocess.run(ffmpeg_cmd, check=True)

    return jsonify({"processed_file": os.path.basename(output_file)})


@app.route("/control/<controlname>", methods=["POST"])
def control_handler(controlname):
    if controlname == "playEnded":
        return playEnded()
    else:
        return jsonify({"error": "Unknown control name"}), 400
    
def playEnded():
    # とりあえず入れただけ
    data = request.json
    songNumber = data.get("songNumber")
    pitch = data.get("pitch")
    print(songNumber, pitch)
    return jsonify({"status":"ok"})


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
