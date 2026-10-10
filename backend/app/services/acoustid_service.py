import logging
import re
from pathlib import Path

import acoustid

from app.config import get_config
from app.repositories.song_repository import SongRepository
from app.services.artist_parsing import normalize_artist_name, parse_song_artists

logger = logging.getLogger(__name__)

# Below this, a match that names the song differently isn't worth suggesting.
_MIN_SUGGEST_SCORE = 0.9

_RELEASE_TYPE_PRIORITY: dict[str, int] = {"Album": 0, "EP": 1, "Single": 2}


def _parse_candidates(raw_data: dict) -> list[dict]:
    """
    Parse a raw AcoustID API response into a list of candidate dicts sorted by score descending.

    Each candidate contains:
      score, recordingId, title, artist, releases (list of all album titles),
      year (earliest release year), release_type_priority (0=LP, 1=EP, 2=Single, 3=unknown),
      album (title from the best-typed release)
    """
    candidates = []
    if raw_data.get("status") != "ok" or "results" not in raw_data:
        return candidates

    for result in raw_data["results"]:
        score = result["score"]
        for recording in result.get("recordings") or []:
            artists = recording.get("artists") or []
            artist_name = (
                "".join(a["name"] + a.get("joinphrase", "") for a in artists) or None
            )
            raw_releases = recording.get("releases") or []
            releases = [r["title"] for r in raw_releases if r.get("title")]
            years = [
                r["date"]["year"]
                for r in raw_releases
                if r.get("date") and r["date"].get("year")
            ]
            year = min(years) if years else None

            # Find the best release type and its album title
            best_priority = 3
            best_album: str | None = releases[0] if releases else None
            for r in raw_releases:
                rtype = (r.get("releasegroup") or {}).get("type")
                priority = _RELEASE_TYPE_PRIORITY.get(rtype, 3)
                if priority < best_priority and r.get("title"):
                    best_priority = priority
                    best_album = r["title"]

            candidates.append(
                {
                    "score": score,
                    "recordingId": recording["id"],
                    "title": recording.get("title"),
                    "artist": artist_name,
                    "releases": releases,
                    "year": year,
                    "release_type_priority": best_priority,
                    "album": best_album,
                }
            )

    # Deduplicate by recordingId, keeping the highest score for each
    seen: dict[str, dict] = {}
    for c in candidates:
        rid = c["recordingId"]
        if rid not in seen or c["score"] > seen[rid]["score"]:
            seen[rid] = c
    return sorted(seen.values(), key=lambda c: c["score"], reverse=True)


def _album_matches(song_album: str, candidate_releases: list[str]) -> bool:
    """Return True if the song's album fuzzy-matches any of the candidate's release titles."""
    needle = song_album.lower().strip()
    return any(needle in r.lower() or r.lower() in needle for r in candidate_releases)


_BRACKETED = re.compile(r"[\(\[].*?[\)\]]")
_VERSION_SUFFIX = re.compile(
    r"\s+-\s+.*\b(?:remaster(?:ed)?|version|live|mix|edit|mono|stereo)\b.*$",
    re.IGNORECASE,
)


def _title_key(title: str) -> str:
    """A title without its bracketed parts or " - 2011 Remaster"-style suffix."""
    return normalize_artist_name(_VERSION_SUFFIX.sub("", _BRACKETED.sub(" ", title)))


def _artist_words(name: str) -> list[str]:
    """An artist name as comparable words, without a leading "The"."""
    words = [normalize_artist_name(w) for w in name.replace("&", " and ").split()]
    words = [w for w in words if w]
    return words[1:] if words[:1] == ["the"] else words


def _same_artist(a: str, b: str) -> bool:
    """Same name, or one is the other with more after it ("Bob Marley & The Wailers")."""
    if normalize_artist_name(a) == normalize_artist_name(b):
        return True
    wa, wb = _artist_words(a), _artist_words(b)
    shorter, longer = sorted((wa, wb), key=len)
    return bool(shorter) and longer[: len(shorter)] == shorter


def _agrees(
    song_title: str | None,
    song_artist: str | None,
    candidate_title: str | None,
    candidate_artist: str | None,
) -> bool:
    """
    True if an AcoustID candidate names the same song the song already says it is.

    Spelling, case, bracketed parts ("(Remix)", "(feat. X)") and version suffixes
    don't count as differences. Artists agree when any credited name matches,
    or when one name runs on from the other.
    """
    if not (song_title and song_artist and candidate_title and candidate_artist):
        return False
    title_key = _title_key(song_title)
    if not title_key or title_key != _title_key(candidate_title):
        return False

    def names(artist_str: str) -> list[str]:
        primary, featured = parse_song_artists(artist_str)
        return [artist_str, primary, *featured]

    return any(
        _same_artist(a, b) for a in names(song_artist) for b in names(candidate_artist)
    )


_NO_SUGGESTION = {
    "acoustid_suggested_recording_id": None,
    "acoustid_suggested_title": None,
    "acoustid_suggested_artist": None,
}


class AcoustIdService:
    def __init__(self, song_repo: SongRepository):
        self.song_repo = song_repo

    def fingerprint_and_link(self, song_id: str, audio_path: str | Path) -> str:
        """
        Fingerprint audio via AcoustID and link the MusicBrainz recording it finds.

        Never changes the song's title or artist:
        - a candidate that agrees with them is linked ("matched"), at any score;
        - a confident (>= 0.9) candidate that names the song differently is kept
          as a suggestion for a person to accept or turn down ("suggested");
        - tied candidates that don't agree are narrowed by album, else "ambiguous".

        A song whose names a person confirmed keeps its names and recording;
        AcoustID only links a recording to it when there's none and it agrees.

        Returns the fingerprint status it set.
        """
        api_key = get_config().ACOUSTID_API_KEY
        if not api_key:
            logger.warning(
                "ACOUSTID_API_KEY not configured; skipping fingerprinting for song %s",
                song_id,
            )
            return self._unresolved(song_id, "failed")

        try:
            raw = acoustid.match(
                api_key,
                str(audio_path),
                meta=["recordings", "releases"],
                parse=False,
            )
        except acoustid.FingerprintGenerationError as e:
            logger.warning("AcoustID: fpcalc failed for song %s: %s", song_id, e)
            return self._unresolved(song_id, "failed")
        except acoustid.WebServiceError as e:
            logger.warning("AcoustID: web service error for song %s: %s", song_id, e)
            return self._unresolved(song_id, "failed")
        except Exception:
            logger.warning(
                "AcoustID: unexpected error for song %s", song_id, exc_info=True
            )
            return self._unresolved(song_id, "failed")

        candidates = _parse_candidates(raw)
        if not candidates:
            logger.info("AcoustID: no match for song %s", song_id)
            return self._unresolved(song_id, "no_match")

        song = self.song_repo.fetch(song_id)
        if not song:
            logger.warning(
                "AcoustID: song %s disappeared while fingerprinting", song_id
            )
            return "not_found"

        best_score = candidates[0]["score"]
        top = [c for c in candidates if c["score"] == best_score]
        song_album = (song.album or "").strip()

        def by_album(options: list[dict]) -> list[dict]:
            if not song_album:
                return []
            return [c for c in options if _album_matches(song_album, c["releases"])]

        # A fingerprint often maps to the same song on many releases; any of
        # them that agrees with the song's names is the one to link.
        agreeing = [
            c for c in top if _agrees(song.title, song.artist, c["title"], c["artist"])
        ]
        if agreeing:
            on_album = by_album(agreeing)
            return self._link(song, on_album[0] if len(on_album) == 1 else agreeing[0])

        if best_score < _MIN_SUGGEST_SCORE:
            logger.info(
                "AcoustID: best match for song %s scored %.2f and names it differently; not used",
                song_id,
                best_score,
            )
            return self._unresolved(song_id, "no_match", score=best_score)

        if len(top) == 1:
            return self._suggest(song, top[0])

        on_album = by_album(top)
        if len(on_album) == 1:
            return self._suggest(song, on_album[0])

        logger.info(
            "AcoustID ambiguous for song %s: %d candidates tied at score=%.2f, none named like the song",
            song_id,
            len(top),
            best_score,
        )
        return self._unresolved(song_id, "ambiguous", score=best_score)

    def _link(self, song, candidate: dict) -> str:
        """Link an agreeing recording. Title and artist stay as they are."""
        fields: dict = {
            **_NO_SUGGESTION,
            "acoustid_score": candidate["score"],
            "acoustid_fingerprint_status": "matched",
        }
        # A recording a person picked stays picked.
        if not (song.metadata_confirmed_at and song.musicbrainz_recording_id):
            fields["musicbrainz_recording_id"] = candidate["recordingId"]
        self.song_repo.update(song.id, **fields)
        logger.info(
            "AcoustID linked song %s to recording %s (score=%.2f)",
            song.id,
            candidate["recordingId"],
            candidate["score"],
        )
        return "matched"

    def _suggest(self, song, candidate: dict) -> str:
        """Keep a confident match that names the song differently, for review."""
        if song.metadata_confirmed_at:
            # A person already settled this song's names.
            logger.info(
                "AcoustID: song %s is confirmed; not suggesting '%s' by '%s'",
                song.id,
                candidate["title"],
                candidate["artist"],
            )
            return self._unresolved(song.id, "no_match", score=candidate["score"])
        self.song_repo.update(
            song.id,
            acoustid_suggested_recording_id=candidate["recordingId"],
            acoustid_suggested_title=candidate["title"],
            acoustid_suggested_artist=candidate["artist"],
            acoustid_score=candidate["score"],
            musicbrainz_recording_id=None,
            acoustid_fingerprint_status="suggested",
        )
        logger.info(
            "AcoustID suggests song %s is '%s' by '%s' (score=%.2f); kept for review",
            song.id,
            candidate["title"],
            candidate["artist"],
            candidate["score"],
        )
        return "suggested"

    def _unresolved(self, song_id: str, status: str, score: float | None = None) -> str:
        """
        Record that AcoustID couldn't link a recording.

        An unconfirmed song loses any recording an earlier run linked; it no
        longer describes the song. A confirmed song keeps its recording, and
        anything short of a failure leaves it settled rather than back in review.
        """
        song = self.song_repo.fetch(song_id)
        fields: dict = {**_NO_SUGGESTION, "acoustid_score": score}
        if song and song.metadata_confirmed_at:
            if status != "failed":
                status = "matched" if song.musicbrainz_recording_id else "skipped"
        else:
            fields["musicbrainz_recording_id"] = None
        self.song_repo.update(song_id, acoustid_fingerprint_status=status, **fields)
        return status

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

        _PRIORITY_TO_LABEL = {0: "Album", 1: "EP", 2: "Single"}

        # Sort by year ascending (None last), then release type (LP first)
        sorted_candidates = sorted(
            candidates,
            key=lambda c: (c["year"] or float("inf"), c["release_type_priority"]),
        )
        return [
            {
                "score": c["score"],
                "recordingId": c["recordingId"],
                "title": c["title"],
                "artist": c["artist"],
                "album": c["album"],
                "year": c["year"],
                "releaseType": _PRIORITY_TO_LABEL.get(c["release_type_priority"]),
            }
            for c in sorted_candidates
        ]
