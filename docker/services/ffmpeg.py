import subprocess
import math

def apply_pitch_to_audio(input_path, output_path, pitch):
    try:
        factor = 2 ** (pitch / 12)
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", input_path,
            "-af", f"rubberband=pitch={factor:.5f}",
            "-acodec", "libmp3lame",
            output_path
        ]
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def apply_pitch_to_video(input_path, output_path, pitch):
    try:
        factor = 2 ** (pitch / 12)
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", input_path,
            "-af", f"rubberband=pitch={factor:.5f}",
            "-c:v", "copy",  # 映像は変換しない
            output_path
        ]
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError:
        return False
