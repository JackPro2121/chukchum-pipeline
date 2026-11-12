import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import uuid
from pathlib import Path

from config import BRAND, ENHANCED_DIR, WATERMARK_FONT

Path(ENHANCED_DIR).mkdir(parents=True, exist_ok=True)

ROOT = Path(__file__).resolve().parent.parent
FFMPEG_SKILL_SCRIPTS = ROOT / ".agents" / "skills" / "ffmpeg-skill" / "scripts"

_FONT_CANDIDATES = [
    WATERMARK_FONT,
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
]


def _font_path() -> str | None:
    for candidate in _FONT_CANDIDATES:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def _ff_path(p: str) -> str:
    """Escape a path for FFmpeg filter options (supports Windows colons and slashes)."""
    return p.replace("\\", "/").replace(":", "\\:")


def _probe_media(input_path: str) -> dict:
    """Probe source stream geometry, fps, duration, and audio presence via ffmpeg-skill probe.py."""
    probe_script = FFMPEG_SKILL_SCRIPTS / "probe.py"
    if probe_script.exists():
        proc = subprocess.run(
            [sys.executable, str(probe_script), input_path, "--json"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            try:
                data = json.loads(proc.stdout)
                if isinstance(data, list) and data:
                    data = data[0]
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                pass
    # Direct ffprobe fallback
    proc = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", input_path],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        return {}
    raw = json.loads(proc.stdout or "{}")
    v = next((s for s in raw.get("streams", []) if s.get("codec_type") == "video"), {})
    a = next((s for s in raw.get("streams", []) if s.get("codec_type") == "audio"), {})
    dur = float((raw.get("format") or {}).get("duration") or v.get("duration") or 30.0)
    return {
        "duration": dur,
        "video": {"width": v.get("width", 1080), "height": v.get("height", 1920)},
        "audio": {"sample_rate": int(a.get("sample_rate") or 48000)} if a else None,
    }


def _check_reels_compliance(output_path: str) -> None:
    """Run ffmpeg-skill check.py --platform reels to log verified output specs."""
    check_script = FFMPEG_SKILL_SCRIPTS / "check.py"
    if not check_script.exists():
        return
    proc = subprocess.run(
        [sys.executable, str(check_script), output_path, "--platform", "reels", "--json"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.stdout.strip():
        try:
            rep = json.loads(proc.stdout)
            ok = bool(rep.get("ok"))
            status = "PASS" if ok else "FAIL"
            fails = [r.get("check") for r in rep.get("checks", []) if r.get("status") == "FAIL"]
            warns = [r.get("check") for r in rep.get("checks", []) if r.get("status") == "WARN"]
            print(f"  [ffmpeg-skill check] status={status} | fails={fails} | warns={warns}")
            return
        except json.JSONDecodeError:
            pass
    print(f"  [ffmpeg-skill check] exit={proc.returncode}")


def _wrap_hook_lines(hook_text: str) -> list[str]:
    clean = re.sub(r"[^\x20-\x7E]", " ", hook_text or "")
    clean = re.sub(r"\s+", " ", clean).strip().upper()
    if not clean:
        clean = "WAIT FOR THE TWIST"
    lines = textwrap.wrap(clean, width=28, max_lines=2, placeholder="")
    return lines or [clean[:28]]


def enhance(input_path: str, profile: str = "branded", hook_text: str = "") -> str:
    """
    Transform a scraped reel into an original, Reels-compliant 1080x1920 CFR 30fps
    BT.709 clip (-14 LUFS / -1.0 dBTP) using ffmpeg-skill framing, motion backdrop,
    meme hook card, safe-zone progress bar, and subtle audio+tempo originality shifts.
    """
    info = _probe_media(input_path)
    src_dur = float(info.get("duration") or 30.0)
    aud = info.get("audio")
    has_audio = bool(aud)
    sr = int((aud or {}).get("sample_rate") or 48000)
    if sr < 22050:
        sr = 48000

    # Subtle +5% tempo & +2.5% pitch shift breaks direct IG->FB audio/frame hash matches
    # while keeping voice pitch and comedic pacing natural.
    speed = 1.05 if src_dur >= 8.0 else 1.0
    pitch_factor = 1.025 if speed > 1.0 else 1.0
    tempo_adjust = speed / pitch_factor

    max_out_dur = 58.0
    src_trim = min(src_dur, max_out_dur * speed) if src_dur > 0 else max_out_dur
    out_dur = max(1.0, src_trim / speed)
    fade_out_st = max(0.2, out_dur - 0.25)

    out = Path(ENHANCED_DIR) / f"{uuid.uuid4().hex}.mp4"
    font = _font_path()
    hook_lines = _wrap_hook_lines(hook_text)

    temp_files: list[Path] = []
    try:
        # Video graph:
        # 1) Trim & retime to CFR 30fps, split into ambient backdrop + active foreground card.
        # 2) Crop outer 10%, keep true aspect ratio (no stretch), apply vivid color + sharpen.
        # 3) Compose into Reels safe zone (leaving top 8% & bottom 20% clear of FB chrome).
        v_chain = [
            f"[0:v]trim=duration={src_trim:.3f},setpts=(PTS-STARTPTS)/{speed:.6f},fps=30,split=2[bg_raw][fg_raw]",
            "[bg_raw]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            "gblur=sigma=28,eq=brightness=-0.26:saturation=0.72,vignette=PI/5[bg]",
            "[fg_raw]crop=iw*0.90:ih*0.90,"
            "scale=1012:1210:force_original_aspect_ratio=decrease:force_divisible_by=2,"
            "eq=contrast=1.08:saturation=1.14:brightness=0.015:gamma=1.02,"
            "unsharp=5:5:0.8:5:5:0.4,"
            "pad=iw+8:ih+8:4:4:color=0x1e1e26[fg]",
            "[bg][fg]overlay=x=(W-w)/2:y=298+(1216-h)/2[v_comp]",
        ]

        # Header banner box (y=156..280, safely below top 8% UI cutoff at y=154)
        cur = "v_comp"
        if font:
            ff_font = _ff_path(font)
            v_chain.append(
                f"[{cur}]drawbox=x=48:y=156:w=984:h=124:color=0x0f1016@0.88:t=fill,"
                f"drawbox=x=48:y=276:w=984:h=4:color=0xffc83d@0.95:t=fill[v_hdr]"
            )
            cur = "v_hdr"

            # Burn each wrapped hook line via temp textfile (zero quote/colon escaping failure)
            line_h = 46
            total_text_h = len(hook_lines) * line_h
            start_y = 156 + max(8, (120 - total_text_h) // 2)
            for idx, line in enumerate(hook_lines):
                tf = Path(tempfile.gettempdir()) / f"chukchum_hook_{uuid.uuid4().hex}.txt"
                tf.write_text(line, encoding="utf-8")
                temp_files.append(tf)
                ff_tf = _ff_path(str(tf))
                nxt = f"v_txt_{idx}"
                y_line = start_y + idx * line_h
                v_chain.append(
                    f"[{cur}]drawtext=fontfile='{ff_font}':textfile='{ff_tf}':"
                    f"fontsize=38:fontcolor=0xffffff:x=(w-text_w)/2:y={y_line}:"
                    f"shadowcolor=black@0.65:shadowx=2:shadowy=2[{nxt}]"
                )
                cur = nxt

            if BRAND:
                bf = Path(tempfile.gettempdir()) / f"chukchum_brand_{uuid.uuid4().hex}.txt"
                bf.write_text(f"@{BRAND}", encoding="utf-8")
                temp_files.append(bf)
                ff_bf = _ff_path(str(bf))
                v_chain.append(
                    f"[{cur}]drawtext=fontfile='{ff_font}':textfile='{ff_bf}':"
                    f"fontsize=24:fontcolor=white@0.55:x=54:y=1482:"
                    f"box=1:boxcolor=0x0f1016@0.45:boxborderw=8[v_brand]"
                )
                cur = "v_brand"

        # Animated watch-retention progress bar right above Facebook Reels bottom 20% UI cutoff (y=1526)
        v_chain.append(f"[{cur}]drawbox=x=0:y=1526:w=1080:h=5:color=0xffffff@0.18:t=fill[v_pbg]")
        v_chain.append(f"color=c=0xffc83d:size=1080x5:r=30:duration={out_dur:.3f}[pbar]")
        v_chain.append(
            f"[v_pbg][pbar]overlay=x='-w+w*min(1,t/{out_dur:.3f})':y=1526:shortest=1,"
            f"format=yuv420p[vout]"
        )

        # Audio chain: pitch+tempo originality transform + -14 LUFS Reels target
        if has_audio:
            a_chain = (
                f"[0:a]atrim=duration={src_trim:.3f},asetpts=PTS-STARTPTS,"
                f"asetrate={sr}*{pitch_factor:.5f},aresample={sr},atempo={tempo_adjust:.6f},"
                f"highpass=f=80,acompressor=threshold=-18dB:ratio=2.5:attack=15:release=120,"
                f"loudnorm=I=-14:TP=-1.0:LRA=11,"
                f"afade=t=in:st=0:d=0.15,afade=t=out:st={fade_out_st:.3f}:d=0.25[aout]"
            )
        else:
            a_chain = f"anullsrc=r=48000:cl=stereo:d={out_dur:.3f}[aout]"

        filter_complex = ";".join(v_chain + [a_chain])
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-nostdin",
            "-i", input_path,
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-map", "[aout]",
            "-map_metadata", "-1",
            "-map_chapters", "-1",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-maxrate", "5M",
            "-bufsize", "10M",
            "-profile:v", "high",
            "-level", "4.1",
            "-pix_fmt", "yuv420p",
            "-colorspace", "bt709",
            "-color_primaries", "bt709",
            "-color_trc", "bt709",
            "-r", "30",
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "48000",
            "-ac", "2",
            "-movflags", "+faststart",
            "-t", f"{out_dur:.3f}",
            str(out),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if proc.returncode != 0 or not out.exists() or out.stat().st_size == 0:
            print("ffmpeg error:", (proc.stderr or "")[-1500:])
            try:
                out.unlink(missing_ok=True)
            except OSError:
                pass
            return input_path

        size_mb = out.stat().st_size / (1024 * 1024)
        print(f"  [enhancer] rendered {out.name} ({size_mb:.2f} MB, ~{out_dur:.1f}s @ {speed}x)")
        _check_reels_compliance(str(out))
        return str(out)
    finally:
        for tf in temp_files:
            try:
                tf.unlink(missing_ok=True)
            except OSError:
                pass
