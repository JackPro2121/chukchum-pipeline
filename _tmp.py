import sqlite3

c = sqlite3.connect("data/state.db")
for r in c.execute("select video_source_url,status,platforms_posted from processed_videos"):
    print(r[0], r[1], r[2])
