"""Artist name parsing — extracts primary + featured artists from a single artist string."""

import re

_FEAT_PATTERN = re.compile(
    r"\s+(?:ft\.?|feat\.?|featuring)\s+", re.IGNORECASE
)
_SPLIT_PATTERN = re.compile(r"\s*,\s*")


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
