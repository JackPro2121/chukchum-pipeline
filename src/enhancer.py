import subprocess
import uuid
from pathlib import Path
from config import ENHANCED_DIR, BRAND

Path(ENHANCED_DIR).mkdir(parents=True, exist_ok=True)


def enhance(input_path: str) -> str:
    out = Path(ENHANCED_DIR) / f"{uuid.uuid4().hex}.mp4"
    vf = (
        "crop=iw*0.94:ih*0.94,scale=1080:1920,"
        f"drawtext=text='{BRAND}':fontcolor=white:fontsize=48:fontfile='C\\:/Windows/Fonts/arial.ttf':x=40:y=80,"
        "setpts=1.04*PTS"
    )
    af = "asetrate=44100*1.03,aresample=44100,atempo=1.0,volume=1.1"
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", vf, "-af", af,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if proc.returncode != 0 or not out.exists():
        print("ffmpeg error:", proc.stderr[-800:])
        return input_path
    return str(out)
