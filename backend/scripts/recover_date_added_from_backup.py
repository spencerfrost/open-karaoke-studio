import re
import sqlite3
from datetime import datetime

BACKUP_DB = "/home/spencer/code/open-karaoke-studio/backend/karaoke.db.bak"
NEW_DB = "/home/spencer/code/open-karaoke-studio/backend/karaoke.db"

backup_conn = sqlite3.connect(BACKUP_DB)
new_conn = sqlite3.connect(NEW_DB)
backup_cur = backup_conn.cursor()
new_cur = new_conn.cursor()

# Regex for a valid ISO 8601 string (YYYY-MM-DDTHH:MM:SS)
iso_regex = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

backup_cur.execute("SELECT id, date_added FROM songs")
rows = backup_cur.fetchall()

updated = 0
skipped = 0
for song_id, old_date in rows:
    if not old_date:
        continue
    iso_str = None
    try:
        # If already ISO, use as is
        if isinstance(old_date, str) and iso_regex.match(old_date):
            iso_str = old_date
            dt = None
        elif isinstance(old_date, str):
            # Try common formats
            dt = None
            for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(old_date, fmt)
                    iso_str = dt.isoformat(sep="T", timespec="seconds")
                    break
                except ValueError:
                    continue
        elif isinstance(old_date, (int, float)):
            dt = datetime.fromtimestamp(float(old_date))
            iso_str = dt.isoformat(sep="T", timespec="seconds")
        else:
            dt = None
        # Sanity check: only if old_date is a string and dt is not None
        if iso_str and dt and isinstance(old_date, str):
            if (
                str(dt.year) in old_date
                and f"{dt.month:02d}" in old_date
                and f"{dt.day:02d}" in old_date
            ):
                new_cur.execute(
                    "UPDATE songs SET date_added = ? WHERE id = ?", (iso_str, song_id)
                )
                updated += 1
            else:
                print(
                    f"[SKIP] {song_id}: Could not confidently convert '{old_date}' -> '{iso_str}'"
                )
                skipped += 1
        elif iso_str and (dt is None):  # Already ISO
            new_cur.execute(
                "UPDATE songs SET date_added = ? WHERE id = ?", (iso_str, song_id)
            )
            updated += 1
        else:
            print(
                f"[SKIP] {song_id}: Could not confidently convert '{old_date}' -> '{iso_str}'"
            )
            skipped += 1
    except (ValueError, TypeError) as e:
        print(f"[ERROR] {song_id}: {old_date} ({e})")
        skipped += 1

new_conn.commit()
print(f"Updated {updated} date_added values. Skipped {skipped}.")
backup_conn.close()
new_conn.close()
