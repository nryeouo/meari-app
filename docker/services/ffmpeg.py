import subprocess


def run_ffmpeg(cmd):
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def pitch_factor(pitch):
    return 2 ** (pitch / 12)


def apply_pitch_to_audio(input_path, output_path, pitch):
    return run_ffmpeg([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", input_path,
        "-af", f"rubberband=pitch={pitch_factor(pitch):.5f}",
        "-acodec", "libmp3lame",
        output_path,
    ])

def apply_pitch_to_video(input_path, output_path, pitch):
    return run_ffmpeg([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", input_path,
        "-af", f"rubberband=pitch={pitch_factor(pitch):.5f}",
        "-c:v", "copy",
        output_path,
    ])
