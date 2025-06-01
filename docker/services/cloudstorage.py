from google.cloud import storage

def get_mp3_blob(song_number):
    client = storage.Client()
    return client.bucket("meari-video").blob(f"preview/{song_number}.mp3")

def download_blob_to_tempfile(blob, dest_path):
    blob.download_to_filename(dest_path)

def get_video_blob(song_number):
    client = storage.Client()
    return client.bucket("meari-video").blob(f"{song_number}.mp4")

def upload_temp_video_blob(song_number, pitch, file_path):
    client = storage.Client()
    blob = client.bucket("meari-temp").blob(f"temp/{song_number}_{pitch:+d}.mp4")
    blob.upload_from_filename(file_path)
    return blob
