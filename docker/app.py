from about_app import *
from firebase_admin import credentials, firestore
from flask import Flask, redirect, jsonify, send_from_directory
from flask_cors import CORS
from google.cloud import storage
import datetime
import firebase_admin
import os
import sqlite3


# from config import base_dir, video_files_dir, resv_api_url
from config import base_dir
from routes import register_blueprints
from utils.common import dict_factory
# VIDEO_DIR = os.path.join(video_files_dir, "video")
# PROCESSED_DIR = os.path.join(video_files_dir, "processed")
# os.makedirs(PROCESSED_DIR, exist_ok=True)


if not firebase_admin._apps:
    try:
        firebase_admin.initialize_app(credentials.ApplicationDefault())
    except Exception:
        firebase_admin.initialize_app()

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
    reservations_ref = db.collection("reservations")

    documents = []
    try:
        documents = list(
            reservations_ref.order_by("order").order_by("created_at").limit(20).stream()
        )
    except Exception:
        try:
            documents = list(reservations_ref.order_by("created_at").limit(20).stream())
        except Exception:
            documents = []

    skip_statuses = {
        "canceled",
        "cancelled",
        "finished",
        "in-progress",
        "playing",
        "done",
    }

    for doc in documents:
        data = doc.to_dict() or {}
        status = data.get("status")
        normalized_status = ""
        if status is not None:
            normalized_status = str(status).replace("_", "-").replace(" ", "-").lower()
        if normalized_status in skip_statuses:
            continue

        song = {"id": doc.id}

        if "songNumber" in data:
            song["songNumber"] = data["songNumber"]

        order_value = data.get("order")
        if order_value is not None:
            if isinstance(order_value, (int, float)):
                song["order"] = order_value
            else:
                try:
                    song["order"] = int(order_value)
                except (TypeError, ValueError):
                    # Skip entries with non-numeric order values
                    continue

        for field in ("status", "source"):
            if field in data:
                song[field] = data[field]

        created_at = data.get("created_at")
        if created_at is not None:
            timestamp_value = None
            if isinstance(created_at, datetime.datetime):
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=datetime.timezone.utc)
                timestamp_value = int(created_at.timestamp())
            elif hasattr(created_at, "seconds") and hasattr(created_at, "nanoseconds"):
                timestamp_value = int(created_at.seconds + created_at.nanoseconds / 1_000_000_000)

            if timestamp_value is not None:
                song["created_at"] = timestamp_value

        return jsonify({"has_next": True, "song": song})

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
