import logging
from pathlib import Path

import acoustid

from app.config import get_config
from app.repositories.song_repository import SongRepository

logger = logging.getLogger(__name__)

_MIN_AUTO_CORRECT_SCORE = 0.9


def _parse_candidates(raw_data: dict) -> list[dict]:
    """
    Parse a raw AcoustID API response into a list of candidate dicts sorted by score descending.

    Each candidate contains:
      score, recordingId, title, artist, releases (list of all album titles)
    """
    candidates = []
    if raw_data.get("status") != "ok" or "results" not in raw_data:
        return candidates

    for result in raw_data["results"]:
        score = result["score"]
        for recording in result.get("recordings") or []:
            artists = recording.get("artists") or []
            artist_name = "".join(
                a["name"] + a.get("joinphrase", "") for a in artists
            ) or None
            releases = [
                r["title"]
                for r in (recording.get("releases") or [])
                if r.get("title")
            ]
            candidates.append(
                {
                    "score": score,
                    "recordingId": recording["id"],
                    "title": recording.get("title"),
                    "artist": artist_name,
                    "releases": releases,
                }
            )

    return sorted(candidates, key=lambda c: c["score"], reverse=True)


def _album_matches(song_album: str, candidate_releases: list[str]) -> bool:
    """Return True if the song's album fuzzy-matches any of the candidate's release titles."""
    needle = song_album.lower().strip()
    return any(
        needle in r.lower() or r.lower() in needle for r in candidate_releases
    )


class AcoustIdService:
    def __init__(self, song_repo: SongRepository):
        self.song_repo = song_repo

    def fingerprint_and_identify(self, song_id: str, audio_path: str | Path) -> None:
        """
        Fingerprint audio via AcoustID and auto-correct metadata if confidence >= 0.9.

        When multiple candidates are tied at the top score >= 0.9 (common for covers/samples),
        the song's stored album name is used as a tiebreaker. If exactly one candidate's
        release list matches the album, that candidate is applied. Otherwise the song is
        flagged as "ambiguous" for human review.

        Updates acoustid_fingerprint_status, acoustid_score, musicbrainz_recording_id on the song.
        If a unique high-confidence match is found, also overwrites song.title and song.artist.
        """
        api_key = get_config().ACOUSTID_API_KEY
        if not api_key:
            logger.warning("ACOUSTID_API_KEY not configured; skipping fingerprinting for song %s", song_id)
            self.song_repo.update(song_id, acoustid_fingerprint_status="failed")
            return

        try:
            raw = acoustid.match(
                api_key,
                str(audio_path),
                meta=["recordings", "releases"],
                parse=False,
            )
        except acoustid.FingerprintGenerationError as e:
            logger.warning("AcoustID: fpcalc failed for song %s: %s", song_id, e)
            self.song_repo.update(song_id, acoustid_fingerprint_status="failed")
            return
        except acoustid.WebServiceError as e:
            logger.warning("AcoustID: web service error for song %s: %s", song_id, e)
            self.song_repo.update(song_id, acoustid_fingerprint_status="failed")
            return
        except Exception:
            logger.warning("AcoustID: unexpected error for song %s", song_id, exc_info=True)
            self.song_repo.update(song_id, acoustid_fingerprint_status="failed")
            return

        candidates = _parse_candidates(raw)

        if not candidates:
            logger.info("AcoustID: no match for song %s", song_id)
            self.song_repo.update(song_id, acoustid_fingerprint_status="no_match")
            return

        best_score = candidates[0]["score"]
        top_candidates = [c for c in candidates if c["score"] == best_score]

        # Handle tied top candidates — common when a fingerprint maps to multiple recordings
        # (e.g. covers, samples, or the same song on many releases).
        if len(top_candidates) >= 2 and best_score >= _MIN_AUTO_CORRECT_SCORE:
            song = self.song_repo.fetch(song_id)
            song_album = (song.album or "").strip() if song else ""

            if song_album:
                album_matches = [
                    c for c in top_candidates if _album_matches(song_album, c["releases"])
                ]
                if len(album_matches) == 1:
                    chosen = album_matches[0]
                    self.song_repo.update(
                        song_id,
                        title=chosen["title"],
                        artist=chosen["artist"],
                        acoustid_score=chosen["score"],
                        musicbrainz_recording_id=chosen["recordingId"],
                        acoustid_fingerprint_status="matched",
                    )
                    logger.info(
                        "AcoustID resolved tie via album for song %s → '%s' by '%s' (album=%r, score=%.2f)",
                        song_id,
                        chosen["title"],
                        chosen["artist"],
                        song_album,
                        chosen["score"],
                    )
                    self._populate_song_artists(song_id, chosen["artist"])
                    return

            # Could not resolve — flag for human review
            self.song_repo.update(
                song_id,
                acoustid_score=best_score,
                acoustid_fingerprint_status="ambiguous",
            )
            logger.info(
                "AcoustID ambiguous for song %s: %d candidates tied at score=%.2f — flagged for review",
                song_id,
                len(top_candidates),
                best_score,
            )
            return

        # Single clear best candidate
        best = top_candidates[0]
        update: dict = {
            "acoustid_score": best["score"],
            "musicbrainz_recording_id": best["recordingId"],
            "acoustid_fingerprint_status": "matched",
        }

        if best["score"] >= _MIN_AUTO_CORRECT_SCORE and best["title"] and best["artist"]:
            update["title"] = best["title"]
            update["artist"] = best["artist"]
            logger.info(
                "AcoustID auto-corrected song %s → '%s' by '%s' (score=%.2f)",
                song_id,
                best["title"],
                best["artist"],
                best["score"],
            )
        else:
            logger.info(
                "AcoustID matched song %s with score=%.2f (below %.2f threshold; no auto-correct)",
                song_id,
                best["score"],
                _MIN_AUTO_CORRECT_SCORE,
            )

        self.song_repo.update(song_id, **update)
        self._populate_song_artists(song_id, update.get("artist") or best["artist"])

    def _populate_song_artists(self, song_id: str, artist_str: str | None) -> None:
        """Re-populate the song_artists join table after a metadata update."""
        if not artist_str:
            return
        try:
            from app.db.database import get_db_session
            from app.services.song_artist_service import populate_song_artists
            from app.repositories.song_repository import SongRepository

            with get_db_session() as session:
                song = SongRepository(session).fetch(song_id)
                if song:
                    populate_song_artists(session, song, artist_str)
        except Exception:
            logger.warning(
                "Failed to populate song_artists after AcoustID for song %s",
                song_id,
                exc_info=True,
            )

    def lookup_candidates(self, audio_path: str | Path) -> list[dict]:
        """
        Run AcoustID fingerprint and return all candidates sorted by score descending.
        Does NOT modify the database — for admin review use only.

        Each candidate: score, recordingId, title, artist, album (primary release title).
        """
        api_key = get_config().ACOUSTID_API_KEY
        if not api_key:
            raise ValueError("ACOUSTID_API_KEY not configured")

        raw = acoustid.match(
            api_key,
            str(audio_path),
            meta=["recordings", "releases"],
            parse=False,
        )

        candidates = _parse_candidates(raw)

        # Flatten releases to a single album string for the frontend display
        return [
            {
                "score": c["score"],
                "recordingId": c["recordingId"],
                "title": c["title"],
                "artist": c["artist"],
                "album": c["releases"][0] if c["releases"] else None,
            }
            for c in candidates
        ]
