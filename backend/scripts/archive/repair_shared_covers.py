"""Repair album covers that dev and prod overwrote in their shared library folder.

Both databases saved covers as covers/album-{album id}.jpg, but number their
albums separately, so a dev album run (2026-11-10) wrote its covers over
prod's. This downloads every release's cover again from its source, saves it
as covers/{source}-{source_id}.jpg (the name album_service now uses), points
each database's albums at it, and then removes the album-*.jpg files neither
database still uses.

A release whose cover can't be fetched gets cover_path NULL, so the
"Find albums" job's "missing" mode looks it up again.

Dry run by default. From backend/ with the venv active:

    python scripts/repair_shared_covers.py --db prod=URL --db dev=URL
    python scripts/repair_shared_covers.py --db prod=URL --db dev=URL --apply
"""

import argparse
import logging
import re
import sys
import time
from pathlib import Path

import requests
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.services.album_service import (  # noqa: E402
    _DEEZER_ALBUM,
    _YTMUSIC_ART_SIZE,
    _YTMUSIC_SIZE_SUFFIX,
    _deezer_cover,
    cover_file_name,
)

logger = logging.getLogger("repair_shared_covers")

GAP_SECONDS = 0.5
TIMEOUT = 15
OLD_NAME = re.compile(r"^album-\d+\.jpg$")


def load_albums(url: str) -> list[dict]:
    with create_engine(url).connect() as conn:
        rows = conn.execute(
            text(
                "select id, source, source_id, cover_path from albums "
                "where cover_path is not null"
            )
        )
        return [dict(row._mapping) for row in rows]


def cover_url(source: str, source_id: str, ytmusic) -> str | None:
    """Where the release's cover can be downloaded, or None if it has none."""
    if source == "ytmusic":
        thumbnails = ytmusic.get_album(source_id).get("thumbnails") or []
        if not thumbnails:
            return None
        return _YTMUSIC_SIZE_SUFFIX.sub(_YTMUSIC_ART_SIZE, thumbnails[-1]["url"])
    if source == "deezer":
        response = requests.get(_DEEZER_ALBUM.format(id=source_id), timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        if data.get("error"):
            raise RuntimeError(f"Deezer: {data['error']}")
        return _deezer_cover(data.get("cover_xl"))
    if source == "itunes":
        response = requests.get(
            "https://itunes.apple.com/lookup", params={"id": source_id}, timeout=TIMEOUT
        )
        response.raise_for_status()
        results = response.json().get("results") or []
        art = results[0].get("artworkUrl100") if results else None
        return art.replace("100x100bb", "1200x1200bb") if art else None
    raise ValueError(f"unknown source {source!r}")


def download(url: str, dest: Path) -> None:
    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    if not response.headers.get("content-type", "").startswith("image/"):
        raise ValueError(f"not an image: {response.headers.get('content-type')}")
    partial = dest.with_suffix(".part")
    partial.write_bytes(response.content)
    partial.replace(dest)


def fetch_releases(releases: set[tuple[str, str]], library: Path) -> dict:
    """Download each release's cover. Returns {release: relative path or None}."""
    from ytmusicapi import YTMusic

    ytmusic = YTMusic()
    saved: dict[tuple[str, str], str | None] = {}
    for i, (source, source_id) in enumerate(sorted(releases), 1):
        relative = cover_file_name(source, source_id)
        dest = library / relative
        if dest.exists():  # saved by an earlier, interrupted run
            saved[(source, source_id)] = relative
            continue
        try:
            url = cover_url(source, source_id, ytmusic)
            if url:
                download(url, dest)
                saved[(source, source_id)] = relative
            else:
                logger.warning("%s %s has no cover", source, source_id)
                saved[(source, source_id)] = None
        except Exception as e:
            logger.warning("%s %s failed: %s", source, source_id, e)
            saved[(source, source_id)] = None
        if i % 50 == 0:
            logger.info("%d / %d releases", i, len(releases))
        time.sleep(GAP_SECONDS)
    return saved


def update_database(url: str, albums: list[dict], saved: dict) -> tuple[int, int]:
    pointed = cleared = 0
    with create_engine(url).begin() as conn:
        for album in albums:
            path = saved.get((album["source"], album["source_id"]))
            if path:
                conn.execute(
                    text(
                        "update albums set cover_path = :p, image_status = 'found' "
                        "where id = :id"
                    ),
                    {"p": path, "id": album["id"]},
                )
                pointed += 1
            else:
                conn.execute(
                    text(
                        "update albums set cover_path = null, "
                        "image_status = 'not_checked' where id = :id"
                    ),
                    {"id": album["id"]},
                )
                cleared += 1
    return pointed, cleared


def remove_old_files(urls: dict[str, str], library: Path) -> int:
    """Delete album-*.jpg files no database points at any more."""
    in_use = {
        album["cover_path"] for url in urls.values() for album in load_albums(url)
    }
    removed = 0
    for path in (library / "covers").iterdir():
        if OLD_NAME.match(path.name) and f"covers/{path.name}" not in in_use:
            path.unlink()
            removed += 1
    return removed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Repair album covers in the shared library."
    )
    parser.add_argument("--db", action="append", required=True, help="name=URL")
    parser.add_argument("--library", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    urls = dict(item.split("=", 1) for item in args.db)
    albums = {name: load_albums(url) for name, url in urls.items()}
    releases = {
        (a["source"], a["source_id"])
        for rows in albums.values()
        for a in rows
        if a["source"] and a["source_id"]
    }
    for name, rows in albums.items():
        logger.info("%s: %d albums with a cover", name, len(rows))
    logger.info("%d distinct releases to download", len(releases))
    if not args.apply:
        logger.info("Dry run: pass --apply to download and update")
        return

    saved = fetch_releases(releases, args.library)
    failed = [r for r, path in saved.items() if path is None]
    logger.info("downloaded %d, failed %d", len(saved) - len(failed), len(failed))
    for name, url in urls.items():
        pointed, cleared = update_database(url, albums[name], saved)
        logger.info("%s: %d albums repointed, %d cleared", name, pointed, cleared)
    logger.info(
        "removed %d old album-*.jpg files", remove_old_files(urls, args.library)
    )


if __name__ == "__main__":
    main()
