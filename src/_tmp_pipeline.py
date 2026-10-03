import sys
sys.path.insert(0, ".")
from config import DOWNLOAD_DIR, ENHANCED_DIR
from pathlib import Path

enhanced = sorted(Path(ENHANCED_DIR).glob("*.mp4"), key=lambda p: p.stat().st_mtime)
print([str(p) for p in enhanced])
if enhanced:
    import media_repo
    try:
        url = media_repo.add(str(enhanced[-1]))
        print("public url:", url)
    except Exception as e:
        print("media_repo error:", e)
