import os
import subprocess
import uuid
from pathlib import Path

from config import ENHANCED_DIR, BRAND, WATERMARK_FONT

Path(ENHANCED_DIR).mkdir(parents=True, exist_ok=True)

_FONT_CANDIDATES = [
    WATERMARK_FONT,
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


def _watermark_font() -> str | None:
    for candidate in _FONT_CANDIDATES:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def _video_filter() -> str:
    filters = [
        "crop=iw*0.96:ih*0.96",
        "scale=1080:1920:flags=lanczos",
        "setsar=1",
        "eq=contrast=1.06:saturation=1.08:brightness=0.02",
        "unsharp=5:5:0.7:5:5:0.7",
        "format=yuv420p",
    ]
    font = _watermark_font()
    if font and BRAND:
        # FFmpeg on Windows needs the drive-letter colon escaped in filter strings.
        ffmpeg_font = font.replace(":", "\\:")
        drawtext = (
            f"drawtext=fontfile='{ffmpeg_font}':text='{BRAND}':"
            "fontcolor=white@0.28:fontsize=28:"
            "x=W-tw-36:y=H-th-36:shadowcolor=black@0.45:shadowx=2:shadowy=2"
        )
        filters.insert(-1, drawtext)
    return ",".join(filters)


def _audio_filter() -> str:
    return (
        "loudnorm=I=-16:TP=-1.5:LRA=11,"
        "afade=t=in:st=0:d=0.2,"
        "afade=t=out:st=59.8:d=0.2"
    )


def enhance(input_path: str, profile: str = "branded") -> str:
    out = Path(ENHANCED_DIR) / f"{uuid.uuid4().hex}.mp4"
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-t", "60",
        "-vf", _video_filter(),
        "-af", _audio_filter(),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-profile:v", "high",
        "-level", "4.1",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "48000",
        "-movflags", "+faststart",
        str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if proc.returncode != 0 or not out.exists() or out.stat().st_size == 0:
        print("ffmpeg error:", (proc.stderr or "")[-1200:])
        try:
            out.unlink(missing_ok=True)
        except OSError:
            pass
        return input_path
    return str(out)
