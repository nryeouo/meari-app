from flask import Blueprint, request, jsonify
from services.cloudstorage import get_video_blob, upload_temp_video_blob
from services.ffmpeg import apply_pitch_to_video
import tempfile

convert_bp = Blueprint("convert", __name__)

@convert_bp.route("/convert", methods=["POST"])
def convert_video():
    data = request.json
    song_number = data.get("song_number")
    pitch = int(data.get("pitch", 0))

    input_blob = get_video_blob(song_number)
    if not input_blob or not input_blob.exists():
        return jsonify({"error": "video not found"}), 404

    if pitch == 0:
        url = input_blob.generate_signed_url(
            version="v4",
            expiration=900,
            method="GET"
        )
        return jsonify({"processed_file": url})

    with tempfile.NamedTemporaryFile(suffix=".mp4") as temp_input, \
         tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_output:

        input_blob.download_to_filename(temp_input.name)

        success = apply_pitch_to_video(temp_input.name, temp_output.name, pitch)
        if not success:
            return jsonify({"error": "ffmpeg pitch change failed"}), 500

        output_blob = upload_temp_video_blob(song_number, pitch, temp_output.name)

        url = output_blob.generate_signed_url(
            version="v4",
            expiration=900,
            method="GET"
        )
        return jsonify({"processed_file": url})
