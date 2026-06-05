import datetime

from google.cloud import storage

VIDEO_BUCKET = "meari-video"
TEMP_BUCKET = "meari-temp"


def get_bucket(name=VIDEO_BUCKET):
    return storage.Client().bucket(name)


def signed_url(blob, minutes=15):
    return blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(minutes=minutes),
        method="GET",
    )


def get_mp3_blob(song_number):
    return get_bucket().blob(f"preview/{song_number}.mp3")

def download_blob_to_tempfile(blob, dest_path):
    blob.download_to_filename(dest_path)

def get_video_blob(song_number):
    return get_bucket().blob(f"{song_number}.mp4")

def upload_temp_video_blob(song_number, pitch, file_path):
    blob = get_bucket(TEMP_BUCKET).blob(f"temp/{song_number}_{pitch:+d}.mp4")
    blob.upload_from_filename(file_path)
    return blob


def list_bgm_files():
    return [
        blob.name.replace("bgm/", "")
        for blob in get_bucket().list_blobs(prefix="bgm/")
        if blob.name.endswith(".mp3")
    ]


def get_bgm_blob(filename):
    return get_bucket().blob(f"bgm/{filename}")
