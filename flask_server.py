from flask import Flask, abort, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sqlite3
import subprocess

from config import base_dir, video_files_dir

app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app)


VIDEO_DIR = os.path.join(video_files_dir, "video")
PROCESSED_DIR = os.path.join(video_files_dir, "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)


def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}


@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")

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

    print(output_file)

    return jsonify({"processed_file": os.path.basename(output_file)})


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
