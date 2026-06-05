from about_app import *
from flask import Flask, redirect, jsonify, send_from_directory
from flask_cors import CORS

from routes import register_blueprints
from services.cloudstorage import get_bgm_blob, get_bucket, list_bgm_files, signed_url

about = aboutApp()
version_info_dict = {"name": about.name,
                     "version": about.version, "owner": about.owner}

app = Flask(__name__, static_folder="static", static_url_path="/static")
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
    from services.firestore import read_current_event

    event = read_current_event()
    return jsonify(event) if event else (jsonify({}), 204)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.static_folder, "favicon.ico")


@app.route("/next_reserved_song")
def next_reserved_song():
    from services.firestore import read_next_reserved_songs

    return jsonify(read_next_reserved_songs())


@app.route("/bgm_list")
def bgm_list():
    return jsonify(list_bgm_files())


@app.route("/video/<filename>")
def get_signed_video_url(filename):
    blob = get_bucket().blob(filename)
    if not blob.exists():
        return jsonify({"error": "File not found"}), 404

    return jsonify({"url": signed_url(blob)})


@app.route("/bgm/<filename>")
def get_bgm(filename):
    blob = get_bgm_blob(filename)
    if not blob.exists():
        return jsonify({"error": "not found"}), 404
    return redirect(signed_url(blob))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
