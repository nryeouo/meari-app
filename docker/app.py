from about_app import *
from firebase_admin import credentials, firestore
from flask import Flask, redirect, jsonify, send_from_directory
from flask_cors import CORS
from google.cloud import storage
import datetime
import firebase_admin
import os
import requests
import sqlite3


# from config import base_dir, video_files_dir, resv_api_url
from config import base_dir, resv_api_url
from routes import register_blueprints
from utils.common import dict_factory
# VIDEO_DIR = os.path.join(video_files_dir, "video")
# PROCESSED_DIR = os.path.join(video_files_dir, "processed")
# os.makedirs(PROCESSED_DIR, exist_ok=True)


db = firestore.client()

about = aboutApp()
version_info_dict = {"name": about.name,
                     "version": about.version, "owner": about.owner}

app = Flask(__name__, static_folder="static", static_url_path="/static")
client = storage.Client()
bucket = client.bucket("meari-video")
CORS(app)
register_blueprints(app)


@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/about")
def version_info():
    return jsonify(version_info_dict)


@app.route("/event-info")
def event_info():
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    events_ref = db.collection("karaoke_events")
    latest_event_query = events_ref.order_by("startTime", direction=firestore.Query.DESCENDING).limit(5)
    results = latest_event_query.stream()

    for doc in results:
        event = doc.to_dict()
        start = event.get("startTime")
        end = event.get("endTime")
        if start and end and start <= now < end:
            return jsonify(event)

    return jsonify({}), 204


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.static_folder, "favicon.ico")


@app.route("/next_reserved_song")
def next_reserved_song():
    try:
        res = requests.get(resv_api_url, timeout=3)
        res.raise_for_status()
        return jsonify(res.json())
    except requests.RequestException as e:
        # print("予約システムへの接続エラー:", e)
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


@app.route("/bgm_list")
def bgm_list():
    bucket = storage.Client().bucket("meari-video")
    blobs = list(bucket.list_blobs(prefix="bgm/"))
    bgm_files = [blob.name.replace("bgm/", "") for blob in blobs if blob.name.endswith(".mp3")]
    return jsonify(bgm_files)


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
