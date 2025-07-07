import sqlite3
from datetime import datetime

DB_PATH = "/home/spencer/code/open-karaoke-studio/backend/karaoke.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Fetch all date_added values
cur.execute("SELECT id, date_added FROM songs")
rows = cur.fetchall()

updated = 0
for song_id, date_val in rows:
    if date_val is None:
        continue
    # Try to parse and convert to ISO 8601 string
    try:
        # If already ISO, skip
        if isinstance(date_val, str) and "T" in date_val:
            continue
        # Try parsing common formats
        if isinstance(date_val, str):
            # Try known formats
            for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(date_val, fmt)
                    break
                except ValueError:
                    dt = None
            else:
                dt = None
        elif isinstance(date_val, (int, float)):
            dt = datetime.fromtimestamp(float(date_val))
        else:
            dt = None
        if dt:
            iso_str = dt.isoformat(sep="T", timespec="seconds")
            cur.execute(
                "UPDATE songs SET date_added = ? WHERE id = ?", (iso_str, song_id)
            )
            updated += 1
    except Exception as e:
        print(f"Could not convert date for song {song_id}: {date_val} ({e})")

conn.commit()
print(f"Updated {updated} date_added values to ISO format.")
conn.close()
