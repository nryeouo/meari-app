from flask import Blueprint, jsonify
from services.sqlite import get_songs


songs_bp = Blueprint("songs", __name__)

@songs_bp.route("/songs", methods=["GET"])
def return_song_list():
    return jsonify(get_songs())
