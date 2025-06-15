from flask import Blueprint, current_app, send_from_directory

remote_bp = Blueprint("remote", __name__)

@remote_bp.route("/remote")
def serve_remote():
    return send_from_directory(current_app.static_folder, "remote.html")
