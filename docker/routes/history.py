from flask import Blueprint, jsonify, request
from services.firestore import read_history, write_history, create_history, update_history

history_bp = Blueprint("history", __name__)

@history_bp.route("/history")
def read():
    return jsonify(read_history())

@history_bp.route("/history/create", methods=["POST"])
def create():
    return create_history(request.json)

@history_bp.route("/history/update/<doc_id>", methods=["POST"])
def update(doc_id):
    return update_history(doc_id, request.json)
