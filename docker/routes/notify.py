from flask import Blueprint, jsonify, request
from services.firestore import read_notify_messages

notify_bp = Blueprint("notify", __name__)

@notify_bp.route("/notify/list")
def read_notify():
  return jsonify(read_notify_messages())
