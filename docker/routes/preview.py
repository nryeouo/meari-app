from flask import Blueprint, request, jsonify, redirect, send_file
from services.cloudstorage import get_mp3_blob, download_blob_to_tempfile
from services.ffmpeg import apply_pitch_to_audio
import tempfile

preview_bp = Blueprint("preview", __name__)

@preview_bp.route("/preview/<songNumber>")
def preview_song(songNumber):
    pitch = int(request.args.get("pitch", 0))
    blob = get_mp3_blob(songNumber)

    if not blob or not blob.exists():
        return jsonify({"error": "preview mp3 not found"}), 404

    if pitch == 0:
        url = blob.generate_signed_url(
            version="v4",
            expiration=900,  # 15分
            method="GET"
        )
        return redirect(url)

    with tempfile.NamedTemporaryFile(suffix=".mp3") as temp_input, \
         tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_output:

        download_blob_to_tempfile(blob, temp_input.name)

        success = apply_pitch_to_audio(temp_input.name, temp_output.name, pitch)
        if success:
            return send_file(temp_output.name, mimetype="audio/mpeg")
        else:
            return jsonify({"error": "ffmpeg pitch change failed"}), 500
