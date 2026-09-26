# Backend scripts

Library maintenance lives in the admin UI (Songs → Admin: Library Audit, Duplicates,
Data Quality, AcoustID, Lyrics Alignment) and runs as Celery batch tasks. Add new
maintenance jobs there, not here.

What's left in this folder:

- `manage_users.py`: creates the first admin before anyone can log in. The only script
  shipped in the Docker image.
- `archive/`: finished one-off repairs, kept for reference. Not maintained; they may break
  as the app changes.
  - `backfill_lyrics_line_index.py`: verified 2026-09-25, a dry run changes 0 songs.
  - `repair_acoustid_mislabels.py` + `review_mislabels.py`/`.html`: the 2026-09-25 repair of
    68 songs mislabelled by AcoustID.
- `experiments/`: research code (separation-engine comparisons, ASR and lyric-alignment
  trials). Not maintained.

Run anything here from `backend/` with the venv active, e.g.
`python scripts/manage_users.py list`.
