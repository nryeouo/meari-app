import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from utils.common import get_song_titles

if not firebase_admin._apps:
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred)

db = firestore.client()


def read_history():
    history_ref = db.collection("history")

    docs = (
        history_ref
        .where(filter=firestore.FieldFilter("status", "==", "playFinished"))
        .order_by("updated_at", direction=firestore.Query.DESCENDING)
        .limit(10)
        .stream()
    )

    rows = [{"songNumber": doc.get("songNumber"), "updated_at": doc.get("updated_at")} for doc in docs]

    song_numbers = [row["songNumber"] for row in rows]
    title_dict = get_song_titles(song_numbers)

    count_query = history_ref.where(
        filter=firestore.FieldFilter("status", "==", "playFinished")
    ).count()
    count_result = count_query.get()
    total_count = count_result[0][0].value

    return {
        "totalCount": total_count,
        "recent": [
            {
                "songNumber": str(row["songNumber"]),
                "songTitle": title_dict.get(str(row["songNumber"]), "---"),
                "updated_at": int(datetime.datetime.timestamp(row["updated_at"]))
            }
            for row in rows
        ]
    }


def write_history(songNumber, pitch, status):
    db.collection("history").add({
        "time": datetime.datetime.now(datetime.timezone.utc),
        "songNumber": songNumber,
        "pitch": pitch,
        "status": status
    })


def create_history(data):
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    data["created_at"] = now
    data["events"] = [{
        "status": "songSelected",
        "created_at": now
    }]
    data["status"] = "songSelected"
    doc_ref = db.collection("history").add(data)
    return {"docId": doc_ref[1].id}


def update_history(doc_id, data):

    doc_ref = db.collection("history").document(doc_id)
    doc = doc_ref.get()
    now = datetime.datetime.now(tz=datetime.timezone.utc)

    if not doc.exists:
        return "Not found", 404

    current_data = doc.to_dict()
    final_statuses = ["songCancelled", "playAborted", "playFinished"]
    if current_data["status"] in final_statuses:
        return "Already finalized", 400

    event = {
        "status": data["status"],
        "created_at": now
    }

    update_fields = {
        "status": data["status"],
        "updated_at": now,
        "events": firestore.ArrayUnion([event])
    }

    if "pitch" in data:
        update_fields["pitch"] = data["pitch"]

    doc_ref.update(update_fields)
    return "OK", 200



