import sqlite3

c = sqlite3.connect("data/state.db")
c.execute("UPDATE processed_videos SET status='done', platforms_posted='facebook' WHERE id=8")
c.commit()
for r in c.execute("SELECT video_source_url, status, platforms_posted FROM processed_videos"):
    print(r)
