"""Artist name parsing — extracts primary + featured artists from a single artist string.

The parser is the fallback: credits normally arrive as a list from YouTube
Music or MusicBrainz (see song_artist_service.set_song_credits). It runs for
uploads and for songs a person retypes the artist of.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal, Optional

CreditRole = Literal["primary", "featured"]

_FEAT_PATTERN = re.compile(r"\s+(?:ft\.?|feat\.?|featuring)\s+", re.IGNORECASE)
_SPLIT_PATTERN = re.compile(r"\s*,\s*")
_AND_PATTERN = re.compile(r"\s*&\s*")
_LEADING_THE = re.compile(r"^the\s+")
_NON_WORD = re.compile(r"[\W_]+")
# "Popcaan & IRah", "Bou and Flowdan", "X with Y": the joins between guests.
_GUEST_JOIN = re.compile(r"\s+(?:&|and|with)\s+", re.IGNORECASE)
# "& The Wailers", "and His Orchestra": the join is part of a band name.
_BAND_JOIN = re.compile(r"^(?:the|his|her|their|los|las|les|die|das)\s", re.IGNORECASE)
# "(feat. X)", "[ft. X & Y]" in a title.
_TITLE_FEAT = re.compile(
    r"[(\[]\s*(?:ft\.?|feat\.?|featuring)\s+([^)\]]+)[)\]]", re.IGNORECASE
)
# MusicBrainz writes "Jay‐Z" with U+2010; a typed "Jay-Z" must be the same name.
_UNICODE_HYPHENS = str.maketrans({"‐": "-", "‑": "-"})


@dataclass(frozen=True)
class ArtistCredit:
    """One artist credited on a song, as whatever knows the artists lists them.

    `name` is the artist's name to file them under; `credited_as` is how this
    recording prints it, when that differs ("Dixie Chicks" for The Chicks).
    """

    name: str
    role: CreditRole = "primary"
    musicbrainz_id: Optional[str] = None
    youtube_music_id: Optional[str] = None
    credited_as: Optional[str] = None


def clean_artist_name(name: str) -> str:
    """The name to match and store: plain hyphens, single spaces, trimmed."""
    return " ".join(name.translate(_UNICODE_HYPHENS).split())


def _split_guests(text: str) -> list[str]:
    """Split a featured part into names on ",", "&", "and" and "with".

    A join followed by "The", "His"... stays: "Bob Marley & The Wailers".
    """
    names: list[str] = []
    for piece in _SPLIT_PATTERN.split(text):
        current = ""
        pos = 0
        for match in _GUEST_JOIN.finditer(piece):
            if _BAND_JOIN.match(piece[match.end() :]):
                continue
            current += piece[pos : match.start()]
            names.append(current)
            current = ""
            pos = match.end()
        names.append(current + piece[pos:])
    return [clean_artist_name(n) for n in names if n.strip()]


def parse_song_artists(artist_str: str) -> tuple[str, list[str]]:
    """Parse an artist string into (primary, [featured]).

    Splits on 'ft', 'feat', 'featuring' to separate the primary artist from
    featured collaborators. The featured part is split on ",", "&", "and" and
    "with": band names almost never sit there. The primary part is left whole
    ("Simon & Garfunkel"); split_known_primaries splits it when both halves are
    artists already.

    Examples:
        "Bonobo ft Fink"                    → ("Bonobo", ["Fink"])
        "Bonobo feat. Fink, Joy"            → ("Bonobo", ["Fink", "Joy"])
        "Chase & Status feat. Popcaan & IRah" → ("Chase & Status", ["Popcaan", "IRah"])
        "Simon & Garfunkel"                 → ("Simon & Garfunkel", [])
    """
    parts = _FEAT_PATTERN.split(artist_str, maxsplit=1)
    primary = clean_artist_name(parts[0])
    featured = _split_guests(parts[1]) if len(parts) > 1 else []
    return primary, featured


def parse_title_featured(title: str) -> list[str]:
    """The guests a title names: "Song (feat. X & Y)" → ["X", "Y"].

    The title itself is left as it is.
    """
    names: list[str] = []
    for match in _TITLE_FEAT.finditer(title or ""):
        names.extend(_split_guests(match.group(1)))
    return names


def artist_credit(names: list[str]) -> str:
    """The one artist string a song stores for a list of credited artists.

    The inverse of parse_song_artists: the first name is the primary artist,
    the rest are featured, so "JAY-Z feat. Alicia Keys" parses back to both.

    Examples:
        ["Queen"]                  → "Queen"
        ["JAY-Z", "Alicia Keys"]   → "JAY-Z feat. Alicia Keys"
        []                         → ""
    """
    names = [n.strip() for n in names if n and n.strip()]
    if len(names) <= 1:
        return names[0] if names else ""
    return f"{names[0]} feat. {', '.join(names[1:])}"


def credit_line(credits: list[tuple[str, CreditRole]]) -> str:
    """The artist string for credits with roles: "A & B feat. C, D".

    Like artist_credit, but more than one artist can be primary.
    """
    primaries = [n.strip() for n, role in credits if role == "primary" and n.strip()]
    featured = [n.strip() for n, role in credits if role == "featured" and n.strip()]
    line = " & ".join(primaries)
    if featured:
        line = f"{line} feat. {', '.join(featured)}" if line else ", ".join(featured)
    return line


def normalize_artist_name(name: str) -> str:
    """Reduce an artist name to a key for comparing spellings of the same name.

    Case-folds, folds accents, treats "&" as "and", drops a leading "The", and
    removes punctuation and spaces, so "CeeLo Green" and "Cee Lo Green" (or
    "Beyoncé" and "Beyonce") produce the same key. Letters in non-Latin scripts
    are kept.
    """
    decomposed = unicodedata.normalize("NFKD", name)
    folded = "".join(c for c in decomposed if not unicodedata.combining(c))
    key = _AND_PATTERN.sub(" and ", folded.casefold().strip())
    key = _LEADING_THE.sub("", key)
    return _NON_WORD.sub("", key)
