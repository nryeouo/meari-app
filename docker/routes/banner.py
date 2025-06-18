from flask import Blueprint, redirect, jsonify
from google.cloud import storage
import datetime
import random
import re

banner_bp = Blueprint("banner", __name__)

@banner_bp.route("/banner")
def get_banner():
    client = storage.Client()
    bucket = client.bucket("public_relations")

    pattern = re.compile(r"\d{8}_.+/.+\.jpg$")
    candidates = [blob for blob in bucket.list_blobs() if pattern.match(blob.name)]

    if not candidates:
        return jsonify({"error": "not found"}), 404

    blob = random.choice(candidates)
    url = blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(minutes=15),
        method="GET",
    )
    return redirect(url)
