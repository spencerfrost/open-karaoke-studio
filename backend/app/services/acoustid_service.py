import logging
from pathlib import Path

import acoustid

from app.config import get_config
from app.repositories.song_repository import SongRepository
from app.services import musicbrainz_service

logger = logging.getLogger(__name__)

_MIN_AUTO_CORRECT_SCORE = 0.9


class AcoustIdService:
    def __init__(self, song_repo: SongRepository):
        self.song_repo = song_repo

    def fingerprint_and_identify(self, song_id: str, audio_path: str | Path) -> None:
        """
        Fingerprint audio via AcoustID and auto-correct metadata if confidence >= 0.9.

        Updates acoustid_fingerprint_status, acoustid_score, musicbrainz_recording_id on the song.
        If score >= 0.9 and a title/artist are found, also overwrites song.title and song.artist.
        """
        api_key = get_config().ACOUSTID_API_KEY
        if not api_key:
            logger.warning("ACOUSTID_API_KEY not configured; skipping fingerprinting for song %s", song_id)
            self.song_repo.update(song_id, acoustid_fingerprint_status="failed")
            return

        try:
            results = list(
                acoustid.match(
                    api_key,
                    str(audio_path),
                    meta="recordings releasegroups",
                    parse=True,
                )
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

        if not results:
            logger.info("AcoustID: no match for song %s", song_id)
            self.song_repo.update(song_id, acoustid_fingerprint_status="no_match")
            return

        # Pick the highest-confidence result
        best_score, best_recording_id, best_title, best_artist = None, None, None, None
        for score, recording_id, title, artist in results:
            if best_score is None or score > best_score:
                best_score, best_recording_id, best_title, best_artist = score, recording_id, title, artist

        # If multiple candidates share the top score at the auto-correct threshold,
        # the match is ambiguous (covers/samples commonly produce 10+ tied results).
        # Flag for human review rather than auto-applying a random candidate.
        top_count = sum(1 for score, _, _, _ in results if score == best_score)
        if top_count >= 2 and best_score >= _MIN_AUTO_CORRECT_SCORE:
            self.song_repo.update(
                song_id,
                acoustid_score=best_score,
                acoustid_fingerprint_status="ambiguous",
            )
            logger.info(
                "AcoustID ambiguous for song %s: %d candidates tied at score=%.2f — flagged for review",
                song_id,
                top_count,
                best_score,
            )
            return

        update: dict = {
            "acoustid_score": best_score,
            "musicbrainz_recording_id": best_recording_id,
            "acoustid_fingerprint_status": "matched",
        }

        if best_score >= _MIN_AUTO_CORRECT_SCORE and best_title and best_artist:
            update["title"] = best_title
            update["artist"] = best_artist
            logger.info(
                "AcoustID auto-corrected song %s → '%s' by '%s' (score=%.2f)",
                song_id,
                best_title,
                best_artist,
                best_score,
            )
        else:
            logger.info(
                "AcoustID matched song %s with score=%.2f (below %.2f threshold; no auto-correct)",
                song_id,
                best_score,
                _MIN_AUTO_CORRECT_SCORE,
            )

        self.song_repo.update(song_id, **update)

        # Re-populate song_artists after auto-correct or any new match
        try:
            from app.db.database import get_db_session
            from app.services.song_artist_service import populate_song_artists

            artist_str = update.get("artist") or best_artist
            if artist_str:
                with get_db_session() as session:
                    from app.repositories.song_repository import SongRepository

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

        Returns candidates with enriched metadata: title, artist, album, year, duration.
        """
        api_key = get_config().ACOUSTID_API_KEY
        if not api_key:
            raise ValueError("ACOUSTID_API_KEY not configured")

        response = acoustid.match(
            api_key,
            str(audio_path),
            meta="recordings releasegroups",
            parse=False,
        )
        results = response.get("results", [])

        candidates: list[dict] = []
        seen_recording_ids: set[str] = set()

        for result in results:
            score = result.get("score", 0.0)
            for recording in result.get("recordings") or []:
                recording_id = recording.get("id", "")
                if recording_id in seen_recording_ids:
                    continue
                seen_recording_ids.add(recording_id)

                title = recording.get("title", "")
                artists = recording.get("artists") or []
                artist = " & ".join(a.get("name", "") for a in artists if a.get("name"))
                duration = recording.get("duration")  # seconds, may be None

                # Pick the best releasegroup: prefer Album type over singles/EPs
                releasegroups = recording.get("releasegroups") or []
                album: str | None = None
                year: int | None = None
                if releasegroups:
                    def rg_sort_key(rg: dict) -> int:
                        return 0 if rg.get("type") == "Album" else 1

                    best_rg = sorted(releasegroups, key=rg_sort_key)[0]
                    album = best_rg.get("title") or None
                    # releasegroups don't include date — year filled by MusicBrainz fallback below

                candidates.append(
                    {
                        "score": score,
                        "recordingId": recording_id,
                        "title": title,
                        "artist": artist,
                        "album": album,
                        "year": year,
                        "duration": duration,
                    }
                )

        candidates = sorted(candidates, key=lambda c: c["score"], reverse=True)

        # AcoustID often lacks release data — enrich via MusicBrainz where missing
        for candidate in candidates:
            if candidate["album"] is None and candidate["recordingId"]:
                try:
                    release_info = musicbrainz_service.get_recording_release_info(
                        candidate["recordingId"]
                    )
                    candidate["album"] = release_info["album"]
                    candidate["year"] = release_info["year"]
                except Exception:
                    logger.debug(
                        "MB release lookup failed for recording %s",
                        candidate["recordingId"],
                    )

        return candidates
