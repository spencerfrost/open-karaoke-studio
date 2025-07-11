import os
import sqlite3
from datetime import datetime

# Paths
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../karaoke.db"))

# Connect to the database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Fetch all songs with a date_added value
cursor.execute("SELECT id, date_added FROM songs WHERE date_added IS NOT NULL")
rows = cursor.fetchall()

updated = 0
for song_id, date_str in rows:
    # Try to parse the date in known formats
    dt = None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(date_str, fmt)
            break
        except Exception:
            continue
    if not dt:
        print(f"Could not parse date_added for song {song_id}: {date_str}")
        continue
    # Normalize to ISO 8601 without microseconds
    normalized = dt.strftime("%Y-%m-%dT%H:%M:%S")
    if date_str != normalized:
        cursor.execute(
            "UPDATE songs SET date_added = ? WHERE id = ?", (normalized, song_id)
        )
        updated += 1

conn.commit()
conn.close()

print(f"Normalized date_added for {updated} songs to ISO 8601 (YYYY-MM-DDTHH:MM:SS)")
