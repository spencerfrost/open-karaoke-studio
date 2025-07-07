import os
import sqlite3

# Paths
OLD_DB = "/home/spencer/code/open-karaoke-studio/backend/karaoke.db.bak"
NEW_DB = "/home/spencer/code/open-karaoke-studio/backend/karaoke.db"

# Connect to both databases
old_conn = sqlite3.connect(OLD_DB)
new_conn = sqlite3.connect(NEW_DB)
old_cur = old_conn.cursor()
new_cur = new_conn.cursor()

# Get all rows from old songs table
old_cur.execute("SELECT * FROM songs")
rows = old_cur.fetchall()

# Get column names from old and new tables
old_cur.execute("PRAGMA table_info(songs)")
old_columns = [col[1] for col in old_cur.fetchall()]
new_cur.execute("PRAGMA table_info(songs)")
new_columns = [col[1] for col in new_cur.fetchall()]

# Build mapping: only columns present in both, except duration/duration_ms
common_cols = [
    col for col in new_columns if col in old_columns and col not in ("duration_ms",)
]

# Prepare insert statement for new table
insert_cols = [col for col in new_columns if col != "duration_ms"]
insert_cols.append("duration_ms")
placeholders = ",".join(["?"] * len(insert_cols))
insert_sql = (
    f"INSERT OR REPLACE INTO songs ({','.join(insert_cols)}) VALUES ({placeholders})"
)

# Indexes for mapping
old_col_idx = {col: i for i, col in enumerate(old_columns)}


def get_duration_ms(row):
    # Prefer duration_ms if present, else convert duration (seconds) to ms
    if "duration_ms" in old_col_idx and row[old_col_idx["duration_ms"]] is not None:
        return row[old_col_idx["duration_ms"]]
    elif "duration" in old_col_idx and row[old_col_idx["duration"]] is not None:
        return int(float(row[old_col_idx["duration"]]) * 1000)
    else:
        return None


# Migrate each row
for row in rows:
    values = []
    for col in new_columns:
        if col == "duration_ms":
            values.append(get_duration_ms(row))
        elif col in old_col_idx:
            values.append(row[old_col_idx[col]])
        else:
            values.append(None)
    new_cur.execute(insert_sql, values)

new_conn.commit()
print(f"Migrated {len(rows)} songs from backup to new database.")

old_conn.close()
new_conn.close()
