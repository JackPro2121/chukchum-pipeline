import sys
sys.path.insert(0, ".")
import storage

storage.record_video("https://yt/test", "src", "file", "pub", ["facebook"], caption="cap")
print(storage.all_videos())
