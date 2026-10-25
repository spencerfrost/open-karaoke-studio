"""
Comparing song titles and artist names across sources.

Used wherever two spellings of a song have to be recognized as the same one:
the album lookup's Deezer match rules, and the add-song search, which groups
covers and remakes under the song they copy.

- normalize: lowercase, accents folded, punctuation dropped, "&" as "and".
- title_key: the title without "feat." credits or bracketed notes, so
  "Empire State Of Mind (feat. Alicia Keys)" keys as "empire state of mind".
- song_key: title_key, also without a " - Live" style suffix, so every
  version of a song shares one key.
- version_markers: the words in a title that make a different recording.
"""

import re
import unicodedata

# Markers that make a different recording. A song title carrying one needs a
# matching title carrying it too.
VERSION_MARKERS = frozenset(
    {"live", "acoustic", "remix", "demo", "edit", "version", "unplugged"}
)
# Of those, the ones a matching title can't carry unless the song's does: a
# "Radio Edit" or "Album Version" is the same recording, a live one isn't.
STRICT_MARKERS = frozenset({"live", "acoustic", "remix", "demo", "unplugged"})

_FEAT_ARTIST = re.compile(r"\s+(feat\.?|ft\.?|featuring|with)\s.*$", re.IGNORECASE)
_FEAT_TITLE = re.compile(r"\s+(feat\.?|ft\.?|featuring)\s.*$", re.IGNORECASE)
_BRACKETED = re.compile(r"\s*[\(\[][^\)\]]*[\)\]]")
# " - Remastered 2011", " - Live at Wembley": a suffix after a spaced dash.
_DASH_SUFFIX = re.compile(r"\s+[-–—]\s+.*$")


def normalize(text: str) -> str:
    """Lowercase, no accents or punctuation, "&" as "and", single spaces."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^\w\s]", " ", text).replace("_", " ")
    return " ".join(text.split())


def artist_key(artist: str) -> str:
    """An artist name without featured credits, brackets or a leading "The"."""
    key = normalize(_FEAT_ARTIST.sub("", _BRACKETED.sub("", artist or "")))
    return key[4:] if key.startswith("the ") else key


def title_key(title: str) -> str:
    """A title without featured credits or bracketed notes."""
    return normalize(_FEAT_TITLE.sub("", _BRACKETED.sub("", title or "")))


def song_key(title: str) -> str:
    """title_key without a dash suffix: the same for every version of a song."""
    return title_key(_DASH_SUFFIX.sub("", title or ""))


def version_markers(title: str) -> set[str]:
    """The VERSION_MARKERS words a title carries ("remixed" counts as remix)."""
    words = set(normalize(title).split())
    if "remixed" in words:
        words.add("remix")
    return words & VERSION_MARKERS
