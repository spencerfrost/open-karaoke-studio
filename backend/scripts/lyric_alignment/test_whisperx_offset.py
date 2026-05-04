#!/usr/bin/env python3
"""
Manual test script for WhisperX-derived offset correction.

Workflow:
  1. list                          — find songs with synced lyrics to test with
  2. poison <song_id> <seconds>    — shift synced_lyrics by a known offset (saves backup)
  3. trigger <song_id>             — dispatch the align_song_lyrics Celery task
  4. check <song_id>               — compare current synced_lyrics to backup
  5. restore <song_id>             — put the original lyrics back

Example:
  python test_whisperx_offset.py list
  python test_whisperx_offset.py poison abc123 5.0
  python test_whisperx_offset.py trigger abc123
  # wait for Celery to finish, then:
  python test_whisperx_offset.py check abc123
  python test_whisperx_offset.py restore abc123
"""

import json
import sys
from pathlib import Path

BACKUP_FILE = Path(__file__).parent / ".offset_test_backups.json"


def _load_backups() -> dict:
    if BACKUP_FILE.exists():
        return json.loads(BACKUP_FILE.read_text())
    return {}


def _save_backups(data: dict) -> None:
    BACKUP_FILE.write_text(json.dumps(data, indent=2))


def cmd_list(limit: int = 20) -> None:
    """List songs that have synced_lyrics and are candidates for testing."""
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository

    with get_db_session() as session:
        songs = SongRepository(session).fetch_all()
        candidates = [s for s in songs if s.synced_lyrics][:limit]

    if not candidates:
        print("No songs with synced_lyrics found.")
        return

    print(f"{'ID':<36}  {'Title':<40}  {'Artist':<25}  word_synced")
    print("-" * 110)
    for s in candidates:
        has_word = "yes" if s.word_synced_lyrics else "no"
        print(f"{s.id:<36}  {(s.title or '')[:40]:<40}  {(s.artist or '')[:25]:<25}  {has_word}")


def cmd_poison(song_id: str, offset_seconds: float) -> None:
    """Shift synced_lyrics by offset_seconds and clear word_synced_lyrics."""
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository
    from app.services.lyrics_offset import shift_lrc_timestamps

    backups = _load_backups()
    if song_id in backups:
        print(f"Warning: backup already exists for {song_id}. Restore first or it will be overwritten.")

    with get_db_session() as session:
        song = SongRepository(session).fetch(song_id)
        if not song:
            print(f"Song not found: {song_id}")
            return
        if not song.synced_lyrics:
            print(f"Song {song_id} has no synced_lyrics.")
            return

        original = song.synced_lyrics
        backups[song_id] = {
            "synced_lyrics": original,
            "word_synced_lyrics": song.word_synced_lyrics,
            "applied_offset": offset_seconds,
        }
        _save_backups(backups)

        shifted = shift_lrc_timestamps(original, offset_seconds)
        song.synced_lyrics = shifted
        song.word_synced_lyrics = None
        session.commit()

    print(f"Applied {offset_seconds:+.3f}s offset to synced_lyrics for song {song_id}.")
    print(f"Cleared word_synced_lyrics. Backup saved to {BACKUP_FILE.name}.")
    print("\nFirst 5 lines after poisoning:")
    for line in shifted.splitlines()[:5]:
        print(f"  {line}")


def cmd_trigger(song_id: str) -> None:
    """Dispatch the align_song_lyrics Celery task for the song."""
    from app.jobs.celery_app import celery

    task = celery.send_task("align_song_lyrics", args=[song_id])
    print(f"Dispatched align_song_lyrics for song {song_id}")
    print(f"Task ID: {task.id}")
    print("Watch Celery logs: tmux capture-pane -t open-karaoke:0.2 -p | tail -30")


def cmd_check(song_id: str) -> None:
    """Compare current synced_lyrics to the backup to measure correction accuracy."""
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository
    from app.services.lyrics_analysis import parse_lrc_lines

    backups = _load_backups()
    if song_id not in backups:
        print(f"No backup found for {song_id}. Run 'poison' first.")
        return

    backup = backups[song_id]
    applied_offset = backup["applied_offset"]
    original_lrc = backup["synced_lyrics"]

    with get_db_session() as session:
        song = SongRepository(session).fetch(song_id)
        if not song or not song.synced_lyrics:
            print(f"Song {song_id} not found or has no synced_lyrics.")
            return
        current_lrc = song.synced_lyrics

    original_lines = parse_lrc_lines(original_lrc)
    current_lines = parse_lrc_lines(current_lrc)

    if not original_lines or not current_lines:
        print("Could not parse LRC lines.")
        return

    # Compute actual correction: how much did timestamps shift relative to poisoned version?
    # Poisoned = original + applied_offset
    # Corrected = poisoned - estimated_offset = original + applied_offset - estimated_offset
    # Residual error = current_timestamp - original_timestamp (should be ~0 if correction was perfect)
    n = min(len(original_lines), len(current_lines))
    deltas = [current_lines[i]["timestamp"] - original_lines[i]["timestamp"] for i in range(n)]
    residuals = [abs(d) for d in deltas]

    mean_residual = sum(residuals) / len(residuals) if residuals else 0
    max_residual = max(residuals) if residuals else 0

    print(f"Applied offset (poison): {applied_offset:+.3f}s")
    print(f"Mean residual error vs original: {mean_residual:.3f}s")
    print(f"Max residual error vs original:  {max_residual:.3f}s")

    if mean_residual < 0.5:
        print("Result: GOOD — correction brought lyrics close to original timing")
    elif mean_residual < 1.5:
        print("Result: PARTIAL — some correction applied but residual error is significant")
    else:
        print("Result: POOR — timing is still far from original")

    print("\nSample comparison (original → current, first 8 lines):")
    print(f"  {'Original':>10}  {'Current':>10}  {'Delta':>8}  Text")
    print("  " + "-" * 60)
    for i in range(min(8, n)):
        o = original_lines[i]
        c = current_lines[i]
        delta = c["timestamp"] - o["timestamp"]
        print(f"  {o['timestamp']:>10.3f}  {c['timestamp']:>10.3f}  {delta:>+8.3f}  {o['text'][:40]}")


def cmd_restore(song_id: str) -> None:
    """Restore original synced_lyrics and word_synced_lyrics from backup."""
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository

    backups = _load_backups()
    if song_id not in backups:
        print(f"No backup found for {song_id}.")
        return

    backup = backups[song_id]
    with get_db_session() as session:
        song = SongRepository(session).fetch(song_id)
        if not song:
            print(f"Song not found: {song_id}")
            return
        song.synced_lyrics = backup["synced_lyrics"]
        song.word_synced_lyrics = backup["word_synced_lyrics"]
        session.commit()

    del backups[song_id]
    _save_backups(backups)
    print(f"Restored original synced_lyrics and word_synced_lyrics for song {song_id}.")


COMMANDS = {
    "list": (cmd_list, "list"),
    "poison": (cmd_poison, "poison <song_id> <offset_seconds>"),
    "trigger": (cmd_trigger, "trigger <song_id>"),
    "check": (cmd_check, "check <song_id>"),
    "restore": (cmd_restore, "restore <song_id>"),
}

if __name__ == "__main__":
    # Add project root to path so app imports work
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    args = sys.argv[1:]
    if not args or args[0] not in COMMANDS:
        print("Usage:")
        for _, usage in COMMANDS.values():
            print(f"  python {Path(__file__).name} {usage}")
        sys.exit(1)

    cmd = args[0]
    if cmd == "list":
        cmd_list()
    elif cmd == "poison":
        if len(args) < 3:
            print("Usage: poison <song_id> <offset_seconds>")
            sys.exit(1)
        cmd_poison(args[1], float(args[2]))
    elif cmd == "trigger":
        if len(args) < 2:
            print("Usage: trigger <song_id>")
            sys.exit(1)
        cmd_trigger(args[1])
    elif cmd == "check":
        if len(args) < 2:
            print("Usage: check <song_id>")
            sys.exit(1)
        cmd_check(args[1])
    elif cmd == "restore":
        if len(args) < 2:
            print("Usage: restore <song_id>")
            sys.exit(1)
        cmd_restore(args[1])
