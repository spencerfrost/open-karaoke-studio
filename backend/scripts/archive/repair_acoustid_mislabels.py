#!/usr/bin/env python3
"""
Repair songs whose title/artist were overwritten by a bad AcoustID match.

Before the 2026-03-30 fix, AcoustIdService picked the first of several recordings
tied at the top score and wrote its title/artist over the song's. The audio,
lyrics, and album were left alone, so the song still plays fine but is filed
under the wrong name (e.g. Norah Jones "Don't Know Why" → "Petite Fleur" by
Sidney Bechet). The YouTube metadata saved next to the audio at download time
(original.info.json) still has the truth.

Two steps:

    # 1. Write a review CSV of every song whose title/artist disagrees with its
    #    YouTube metadata, with a proposed correction and a default action.
    python scripts/repair_acoustid_mislabels.py scan --out mislabels.csv

    # 2. Edit the CSV (fix proposals, flip action between fix/keep), then apply.
    #    Without --commit this only prints what would change.
    python scripts/repair_acoustid_mislabels.py apply mislabels.csv
    python scripts/repair_acoustid_mislabels.py apply mislabels.csv --commit

Applying a row sets the new title/artist, re-links song_artists, clears the bad
MusicBrainz recording ID + score, and marks the fingerprint "skipped" so it is
never auto-fingerprinted again. Rows whose DB title/artist changed since the
scan are refused rather than overwritten.
"""

import argparse
import csv
import json
import re
import sys
import unicodedata
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app.config import get_config
from app.db.database import get_db_session
from app.db.models.song import DbSong
from app.services.artist_parsing import parse_song_artists
from app.services.song_artist_service import populate_song_artists

FIELDS = [
    "action",
    "kind",
    "new_title",
    "new_artist",
    "current_title",
    "current_artist",
    "source",
    "youtube_title",
    "youtube_channel",
    "album",
    "fingerprint_status",
    "id",
]

# Parenthesised / bracketed chunks in YouTube titles that are packaging, not title
_JUNK = re.compile(
    r"\s*[\(\[][^\)\]]*\b(official|video|audio|lyrics?|visuali[sz]er|remaster(ed)?|"
    r"hd|4k|hq|uncensored|explicit|vietsub|m/?v)\b[^\)\]]*[\)\]]",
    re.IGNORECASE,
)
_FEAT_IN_TITLE = re.compile(
    r"\s*[\(\[]\s*(?:feat\.?|ft\.?|with)\s+([^\)\]]+)[\)\]]", re.IGNORECASE
)
_SEPARATORS = re.compile(r"\s+(?:-|–|—|///)\s+")


def norm(s: str | None) -> str:
    s = (
        unicodedata.normalize("NFKD", s or "")
        .encode("ascii", "ignore")
        .decode()
        .lower()
    )
    # Drop "(feat. X)" / "[Official Video]" asides — unless that is the whole title, e.g. "(you are here)"
    stripped = re.sub(r"\(.*?\)|\[.*?\]", "", s)
    s = (stripped if stripped.strip() else s).replace("&", "and")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def sim(a: str | None, b: str | None) -> float:
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def join_artists(primary: str, featured: list[str]) -> str:
    seen = {norm(primary)}
    featured = [f for f in featured if f and not (norm(f) in seen or seen.add(norm(f)))]
    return f"{primary} feat. {', '.join(featured)}" if featured else primary


def pull_featured(title: str) -> tuple[str, list[str]]:
    """Split '(feat. X & Y)' out of a title → (clean title, [X, Y])."""
    featured: list[str] = []
    m = _FEAT_IN_TITLE.search(title)
    if m:
        featured = [
            f.strip() for f in re.split(r"\s*(?:,|&| and )\s*", m.group(1)) if f.strip()
        ]
        title = _FEAT_IN_TITLE.sub("", title)
    return title.strip(), featured


def propose(
    info: dict, current_title: str, current_artist: str
) -> tuple[str, str, str]:
    """Best guess at (title, artist, source) from a yt-dlp info.json."""
    yt_artists = info.get("artists") or (
        [a.strip() for a in info["artist"].split(",")] if info.get("artist") else []
    )

    # YouTube Music uploads carry structured track/artist fields — trust them
    if info.get("track") and yt_artists:
        title, feat = pull_featured(info["track"])
        title = _JUNK.sub("", title).strip()
        return (
            title,
            join_artists(yt_artists[0], yt_artists[1:] + feat),
            "youtube-music",
        )

    # Otherwise parse "Artist - Title (Official Video)" out of the video title
    raw = (info.get("title") or "").split(" | ")[0]
    raw = _JUNK.sub("", raw)
    raw = re.sub(r"^\s*\[[^\]]*\]\s*", "", raw)  # leading "[Vietsub+Lyrics]" etc.
    parts = _SEPARATORS.split(raw, maxsplit=1)
    uploader = info.get("uploader") or info.get("channel") or ""
    if len(parts) == 2:
        left, right = (p.strip() for p in parts)
        # "War - Bob Marley": artist is on the right
        if sim(right, current_artist) >= 0.8 or sim(right, uploader) >= 0.8:
            left, right = right, left
        # 'Band - "Song" Some Label' → Song
        quoted = re.match(r"^[\"“](.+?)[\"”]", right)
        right = quoted.group(1) if quoted else right.strip("\"'“”")
        # "SOUNDTRACK - SONG by Artist" → the real artist is after "by"
        if " by " in right:
            right, left = right.rsplit(" by ", 1)
        title, feat = pull_featured(right.strip())
        primary, more = parse_song_artists(left.strip("\"'“”"))
        # "07 Stir It Up - (Bob Marley)" — the "artist" half is really the title; don't trust it
        if sim(primary, current_title) < 0.8:
            return title, join_artists(primary, more + feat), "parsed-title"

    title, feat = pull_featured(raw.strip().strip("\"'“”"))
    return title, join_artists(uploader, feat), "channel-name"


def looks_fine(
    cur_title: str, cur_artist: str, new_title: str, new_artist: str, info: dict
) -> bool:
    """True when the difference is formatting only (feat. style, apostrophes, remaster tags)."""
    if sim(cur_title, new_title) < 0.8:
        return False
    cur_primary, _ = parse_song_artists(cur_artist or "")
    new_primary, _ = parse_song_artists(new_artist or "")
    if sim(cur_primary, new_primary) >= 0.8:
        return True
    # Current primary artist is named somewhere in the YouTube metadata
    blob = " ".join(
        filter(
            None,
            [
                info.get("title"),
                info.get("artist"),
                info.get("uploader"),
                info.get("channel"),
            ],
        )
    )
    return bool(norm(cur_primary)) and norm(cur_primary) in norm(blob)


def classify(
    cur_title: str, cur_artist: str, new_title: str, new_artist: str, fine: bool
) -> str:
    if fine:
        return "formatting only"
    title_same = sim(cur_title, new_title) >= 0.8
    artist_same = (
        sim(
            parse_song_artists(cur_artist or "")[0],
            parse_song_artists(new_artist or "")[0],
        )
        >= 0.8
    )
    if title_same:
        return "different artist, same song"
    if artist_same:
        return "different song, same artist"
    return "title and artist both wrong"


def is_suspect(song: DbSong, info: dict) -> bool:
    """Same test the investigation used: title or artist absent from the YouTube metadata."""
    yt_title = info.get("title") or ""
    yt_track = info.get("track") or ""
    yt_artist = " ".join(
        filter(
            None,
            [
                info.get("artist"),
                info.get("uploader"),
                info.get("channel"),
                " ".join(info.get("artists") or []),
            ],
        )
    )
    blob = f"{yt_title} {yt_track} {yt_artist} {(info.get('description') or '')[:300]}"
    title_ok = max(sim(song.title, yt_title), sim(song.title, yt_track)) >= 0.6
    artist_ok = sim(song.artist, yt_artist) >= 0.6 or (
        bool(norm(song.artist)) and norm(song.artist) in norm(blob)
    )
    return not (title_ok and artist_ok)


def scan(out_path: Path) -> None:
    library = Path(get_config().LIBRARY_DIR)
    rows = []
    missing_info = 0

    with get_db_session() as db:
        for song in db.query(DbSong).order_by(DbSong.artist, DbSong.title):
            info_path = library / song.id / "original.info.json"
            if not info_path.exists():
                missing_info += 1
                continue
            info = json.loads(info_path.read_text())
            if not is_suspect(song, info):
                continue

            new_title, new_artist, source = propose(
                info, song.title or "", song.artist or ""
            )
            fine = looks_fine(song.title, song.artist, new_title, new_artist, info)
            # A bare channel name is too weak a signal to overwrite anything by default
            unchanged = (new_title, new_artist) == (song.title, song.artist)
            action = "keep" if fine or unchanged or source == "channel-name" else "fix"
            rows.append(
                {
                    "action": action,
                    "kind": classify(
                        song.title, song.artist, new_title, new_artist, fine
                    ),
                    "new_title": new_title,
                    "new_artist": new_artist,
                    "current_title": song.title,
                    "current_artist": song.artist,
                    "source": source,
                    "youtube_title": info.get("title"),
                    "youtube_channel": info.get("uploader") or info.get("channel"),
                    "album": song.album,
                    "fingerprint_status": song.acoustid_fingerprint_status,
                    "id": song.id,
                }
            )

    # "fix" rows first — those are the ones worth reading
    rows.sort(
        key=lambda r: (
            r["action"] != "fix",
            r["kind"],
            (r["current_artist"] or "").lower(),
        )
    )
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    fixes = sum(r["action"] == "fix" for r in rows)
    print(
        f"Wrote {len(rows)} rows to {out_path} ({fixes} fix, {len(rows) - fixes} keep)"
    )
    if missing_info:
        print(f"Skipped {missing_info} songs with no original.info.json")


def apply(csv_path: Path, commit: bool) -> None:
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r["action"].strip().lower() == "fix"]

    backup = []
    applied = refused = 0
    with get_db_session() as db:
        for row in rows:
            song = db.get(DbSong, row["id"])
            if song is None:
                print(f"  REFUSED {row['id']}: song no longer exists")
                refused += 1
                continue
            if (song.title, song.artist) != (
                row["current_title"],
                row["current_artist"],
            ):
                print(
                    f"  REFUSED {row['id']}: DB now has '{song.title}' / '{song.artist}', "
                    f"CSV expected '{row['current_title']}' / '{row['current_artist']}' — re-scan"
                )
                refused += 1
                continue

            new_title = row["new_title"].strip()
            new_artist = row["new_artist"].strip()
            if not new_title or not new_artist:
                print(f"  REFUSED {row['id']}: empty new_title/new_artist")
                refused += 1
                continue

            print(
                f"  '{song.title}' / '{song.artist}'  →  '{new_title}' / '{new_artist}'"
            )
            if not commit:
                continue

            backup.append(
                {
                    "id": song.id,
                    "title": song.title,
                    "artist": song.artist,
                    "artist_id": song.artist_id,
                    "musicbrainz_recording_id": song.musicbrainz_recording_id,
                    "acoustid_score": song.acoustid_score,
                    "acoustid_fingerprint_status": song.acoustid_fingerprint_status,
                }
            )
            song.title = new_title
            song.artist = new_artist
            song.musicbrainz_recording_id = None
            song.acoustid_score = None
            song.acoustid_fingerprint_status = "skipped"
            # Commits, and re-points artist_id + song_artists at the new artist
            populate_song_artists(db, song, new_artist)
            applied += 1

    if commit:
        backup_path = csv_path.with_name(
            f"{csv_path.stem}.backup-{datetime.now():%Y%m%d-%H%M%S}.json"
        )
        backup_path.write_text(json.dumps(backup, indent=2))
        print(
            f"\nApplied {applied}, refused {refused}. Previous values saved to {backup_path}"
        )
    else:
        print(
            f"\nDry run: {len(rows) - refused} would change, {refused} refused. Re-run with --commit."
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    scan_p = sub.add_parser("scan", help="write the review CSV")
    scan_p.add_argument("--out", type=Path, default=Path("mislabels.csv"))

    apply_p = sub.add_parser("apply", help="apply rows marked 'fix' in the review CSV")
    apply_p.add_argument("csv", type=Path)
    apply_p.add_argument(
        "--commit", action="store_true", help="actually write to the database"
    )

    args = parser.parse_args()
    if args.command == "scan":
        scan(args.out)
    else:
        apply(args.csv, args.commit)


if __name__ == "__main__":
    main()
