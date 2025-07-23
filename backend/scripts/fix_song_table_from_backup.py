import os
import sqlite3

# Paths
CURRENT_DB = os.path.abspath(os.path.join(os.path.dirname(__file__), "../karaoke.db"))
BACKUP_DB = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../karaoke.db.bak")
)

# Map columns from backup to current schema
# Only map fields that exist in both, and handle renamed fields
COLUMN_MAP = {
    "id": "id",
    "title": "title",
    "artist": "artist",
    "duration_ms": "duration_ms",
    "favorite": "favorite",
    "date_added": "date_added",
    "vocals_path": "vocals_path",
    "instrumental_path": "instrumental_path",
    "original_path": "original_path",
    "thumbnail_path": "thumbnail_path",
    "cover_art_path": "cover_art_path",
    "source": "source",
    "source_url": "source_url",
    "video_id": "video_id",
    "uploader": "uploader",
    "uploader_id": "uploader_id",
    "channel": "channel",
    "channel_id": "channel_id",
    "description": "description",
    "upload_date": "upload_date",
    "mbid": "mbid",
    "album": "album",
    "release_id": "release_id",
    "release_date": "release_date",
    "year": "year",
    "genre": "genre",
    "language": "language",
    "lyrics": "lyrics",
    "synced_lyrics": "synced_lyrics",
    "channel_name": "channel_name",
    "itunes_artist_id": "itunes_artist_id",
    "itunes_collection_id": "itunes_collection_id",
    "track_time_millis": "track_time_millis",
    "itunes_explicit": "itunes_explicit",
    "itunes_preview_url": "itunes_preview_url",
    "youtube_thumbnail_urls": "youtube_thumbnail_urls",
    "youtube_tags": "youtube_tags",
    "youtube_categories": "youtube_categories",
    "youtube_channel_id": "youtube_channel_id",
    "youtube_channel_name": "youtube_channel_name",
    "youtube_raw_metadata": "youtube_raw_metadata",
    # New canonical fields
    "plain_lyrics": "plain_lyrics",
}

# Open connections
src = sqlite3.connect(BACKUP_DB)
dst = sqlite3.connect(CURRENT_DB)
src.row_factory = sqlite3.Row

# Get all rows from backup
rows = src.execute("SELECT * FROM songs").fetchall()

# Prepare insert/update
for row in rows:
    data = {
        dst_col: row[src_col]
        for src_col, dst_col in COLUMN_MAP.items()
        if src_col in row.keys()
    }
    # Upsert by id
    placeholders = ", ".join([f"{col} = ?" for col in data.keys()])
    values = list(data.values())
    values.append(row["id"])
    sql = f"UPDATE songs SET {placeholders} WHERE id = ?"
    cur = dst.execute(sql, values)
    if cur.rowcount == 0:
        # Insert if not exists
        cols = ", ".join(data.keys())
        qs = ", ".join(["?"] * len(data))
        dst.execute(f"INSERT INTO songs ({cols}) VALUES ({qs})", list(data.values()))

dst.commit()
src.close()
dst.close()

print("Song table restored from backup with explicit column mapping.")
