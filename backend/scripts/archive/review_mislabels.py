#!/usr/bin/env python3
"""
Keyboard-driven review UI for the CSV written by repair_acoustid_mislabels.py.

    python scripts/review_mislabels.py ../mislabels.csv
    # → open http://localhost:5199

Shows one song at a time with its thumbnail, playable audio, saved lyrics, and
the proposed rename. Every decision is written straight back into the CSV
(action / new_title / new_artist, plus a "reviewed" column), so when you are
done you run `repair_acoustid_mislabels.py apply` on the same file.
"""

import argparse
import csv
import json
import os
import re
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app.config import get_config
from app.db.database import get_db_session
from app.db.models.song import DbSong
from repair_acoustid_mislabels import FIELDS, norm

PAGE = Path(__file__).with_name("review_mislabels.html")
MEDIA = {"original.mp3": "audio/mpeg", "vocals.mp3": "audio/mpeg", "thumbnail.webp": "image/webp"}
ID_RE = re.compile(r"^[0-9a-f-]{36}$")


class Review:
    """The CSV rows plus the extra context the page needs, guarded by a lock."""

    def __init__(self, csv_path: Path):
        self.csv_path = csv_path
        self.lock = threading.Lock()
        with csv_path.open(newline="", encoding="utf-8-sig") as f:
            self.rows = list(csv.DictReader(f))
        self.fields = FIELDS + ["reviewed"]
        for row in self.rows:
            row.setdefault("reviewed", "")

        ids = [r["id"] for r in self.rows]
        with get_db_session() as db:
            songs = {s.id: s for s in db.query(DbSong).filter(DbSong.id.in_(ids))}
        self.context = {}
        for row in self.rows:
            song = songs.get(row["id"])
            lyrics = (song.plain_lyrics or "") if song else ""
            self.context[row["id"]] = {
                "lyrics": lyrics,
                "videoId": song.video_id if song else None,
                # Lyrics were fetched before the bad rename, so they are independent evidence
                "lyricsMatchNew": _in_lyrics(row["new_title"], lyrics),
                "lyricsMatchCurrent": _in_lyrics(row["current_title"], lyrics),
            }

    def payload(self) -> list[dict]:
        with self.lock:
            return [{**row, **self.context[row["id"]]} for row in self.rows]

    def decide(self, song_id: str, action: str, new_title: str, new_artist: str) -> None:
        with self.lock:
            row = next(r for r in self.rows if r["id"] == song_id)
            row.update(action=action, new_title=new_title, new_artist=new_artist, reviewed="yes")
            # Write-then-rename so a crash never leaves a half-written CSV
            fd, tmp = tempfile.mkstemp(dir=self.csv_path.parent, suffix=".csv")
            with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.fields)
                writer.writeheader()
                writer.writerows(self.rows)
            os.replace(tmp, self.csv_path)


def _in_lyrics(title: str, lyrics: str) -> bool | None:
    if not lyrics.strip():
        return None
    t = norm(title)
    return bool(t) and t in norm(lyrics)


def make_handler(review: Review, library: Path):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):  # noqa: A002 — silence per-request logging
            pass

        def _send(self, status: int, body: bytes, content_type: str, extra: dict | None = None):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/":
                return self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            if self.path == "/api/rows":
                return self._send(200, json.dumps(review.payload()).encode(), "application/json")
            parts = self.path.strip("/").split("/")
            if len(parts) == 3 and parts[0] == "media" and ID_RE.match(parts[1]) and parts[2] in MEDIA:
                return self._media(library / parts[1] / parts[2], MEDIA[parts[2]])
            self._send(404, b"not found", "text/plain")

        def _media(self, path: Path, content_type: str):
            if not path.exists():
                return self._send(404, b"missing", "text/plain")
            size = path.stat().st_size
            start, end = 0, size - 1
            # Range support so the audio element can seek
            m = re.match(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
            if m and (m.group(1) or m.group(2)):
                if m.group(1):
                    start = int(m.group(1))
                    end = int(m.group(2)) if m.group(2) else end
                else:
                    start = size - int(m.group(2))
                end = min(end, size - 1)
            with path.open("rb") as f:
                f.seek(start)
                body = f.read(end - start + 1)
            headers = {"Accept-Ranges": "bytes"}
            if m and (m.group(1) or m.group(2)):
                headers["Content-Range"] = f"bytes {start}-{end}/{size}"
                return self._send(206, body, content_type, headers)
            self._send(200, body, content_type, headers)

        def do_POST(self):
            if self.path != "/api/decide":
                return self._send(404, b"not found", "text/plain")
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if data.get("action") not in ("fix", "keep"):
                return self._send(400, b"bad action", "text/plain")
            review.decide(data["id"], data["action"], data["new_title"].strip(), data["new_artist"].strip())
            self._send(200, b"{}", "application/json")

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--port", type=int, default=5199)
    parser.add_argument("--host", default="127.0.0.1", help="0.0.0.0 to reach it from another machine")
    args = parser.parse_args()

    review = Review(args.csv.resolve())
    server = ThreadingHTTPServer((args.host, args.port), make_handler(review, Path(get_config().LIBRARY_DIR)))
    print(f"Reviewing {len(review.rows)} rows from {args.csv} → http://localhost:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
