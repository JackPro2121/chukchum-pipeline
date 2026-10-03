import subprocess
import uuid
from pathlib import Path
from config import MEDIA_REPO_DIR


def public_url_for(filename: str) -> str:
    return f"https://raw.githubusercontent.com/{MEDIA_REPO}/main/videos/{filename}"


def add(file_path: str) -> str:
    src = Path(file_path)
    dest_dir = Path(MEDIA_REPO_DIR) / "videos"
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.mp4"
    dest = dest_dir / name
    dest.write_bytes(src.read_bytes())
    subprocess.run(["git", "add", f"videos/{name}"], cwd=MEDIA_REPO_DIR, check=True)
    subprocess.run(["git", "commit", "-m", f"add {name}"], cwd=MEDIA_REPO_DIR, check=True)
    subprocess.run(["git", "push"], cwd=MEDIA_REPO_DIR, check=True)
    return public_url_for(name)


def remove(filename: str):
    path = Path(MEDIA_REPO_DIR) / "videos" / filename
    if path.exists():
        subprocess.run(["git", "rm", f"videos/{filename}"], cwd=MEDIA_REPO_DIR, check=True)
        subprocess.run(["git", "commit", "-m", f"prune {filename}"], cwd=MEDIA_REPO_DIR, check=True)
        subprocess.run(["git", "push"], cwd=MEDIA_REPO_DIR, check=True)
        path.unlink(missing_ok=True)
