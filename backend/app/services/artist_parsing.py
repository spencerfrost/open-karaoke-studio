"""Artist name parsing — extracts primary + featured artists from a single artist string."""

import re
import unicodedata

_FEAT_PATTERN = re.compile(r"\s+(?:ft\.?|feat\.?|featuring)\s+", re.IGNORECASE)
_SPLIT_PATTERN = re.compile(r"\s*,\s*")
_AND_PATTERN = re.compile(r"\s*&\s*")
_LEADING_THE = re.compile(r"^the\s+")
_NON_WORD = re.compile(r"[\W_]+")


def parse_song_artists(artist_str: str) -> tuple[str, list[str]]:
    """Parse an artist string into (primary, [featured]).

    Splits on 'ft', 'feat', 'featuring' to separate the primary artist from
    featured collaborators. The featured portion is then split on commas only
    (ampersand '&' is NOT a split delimiter — "Simon & Garfunkel" stays whole).

    Examples:
        "Bonobo ft Fink"           → ("Bonobo", ["Fink"])
        "Bonobo feat. Fink, Joy"   → ("Bonobo", ["Fink", "Joy"])
        "Simon & Garfunkel"        → ("Simon & Garfunkel", [])
        "Bonobo"                   → ("Bonobo", [])
    """
    parts = _FEAT_PATTERN.split(artist_str, maxsplit=1)
    primary = parts[0].strip()
    if len(parts) > 1:
        featured = [a.strip() for a in _SPLIT_PATTERN.split(parts[1])]
        featured = [f for f in featured if f]
    else:
        featured = []
    return primary, featured


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
