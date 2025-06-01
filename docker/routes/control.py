from flask import Blueprint, jsonify, request
from services.firestore import write_history

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
    return jsonify({"status": "ok"})
