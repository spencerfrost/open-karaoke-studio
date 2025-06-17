"""
Database migration script to add new columns to the songs table
"""

import sqlite3
from pathlib import Path

# Path to the SQLite database
DB_PATH = Path(__file__).resolve().parent.parent.parent / "karaoke.db"


def add_lyrics_columns():
    """Add lyrics and synced_lyrics columns to the songs table if they don't exist"""
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check if the columns already exist
        cursor.execute("PRAGMA table_info(songs)")
        columns = [column[1] for column in cursor.fetchall()]

        # Add lyrics column if it doesn't exist
        if "lyrics" not in columns:
            print("Adding lyrics column to songs table...")
            cursor.execute("ALTER TABLE songs ADD COLUMN lyrics TEXT")

        # Add synced_lyrics column if it doesn't exist
        if "synced_lyrics" not in columns:
            print("Adding synced_lyrics column to songs table...")
            cursor.execute("ALTER TABLE songs ADD COLUMN synced_lyrics TEXT")

        # Commit changes
        conn.commit()
        print("Migration completed successfully.")

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    print(f"Running database migration on {DB_PATH}")
    add_lyrics_columns()
