from flask import Blueprint, jsonify, request
from services.firestore import (
    delete_reservations_by_song_number,
    write_history,
)
from utils.common import get_song_titles

control_bp = Blueprint("control", __name__)

@control_bp.route("/control/<controlname>", methods=["POST"])
def control_handler(controlname):
    valid_statuses = {"playStarted", "playEnded", "playAborted"}
    if controlname in valid_statuses:
        return handle_play_event(controlname)
    return jsonify({"error": "Unknown control name"}), 400


def handle_play_event(status):
    data = request.json
    songNumber = data.get("songNumber")
    pitch = data.get("pitch")
    write_history(songNumber, pitch, status)

    if status == "playStarted" and songNumber:
        delete_reservations_by_song_number(songNumber)

    """
    if status == "playStarted" and songNumber:
        titles = get_song_titles([songNumber])
        song_title = titles.get(str(songNumber), "")
        webhook_url = (
            "https://discord.com/api/webhooks/1399660842559078491/"
            "RNSyEiYtJkusHCLzBpfI74rWPSOhb68T7h3ot2GjjZER9HOowRCv19Z3CQdLIYrUUAl_"
        )
        message = f"\U0001F50A \u518D\u751F\u4E2D: `{songNumber}` 《{song_title}》"
        try:
            requests.post(webhook_url, json={"content": message}, timeout=5)
        except requests.RequestException:
            pass
    """

    return jsonify({"status": "ok"})
