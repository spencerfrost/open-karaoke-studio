"""
How artist and show names are filed in the A–Z browse lists.

One place, so every list that groups by letter agrees: the phone's A–Z bar
and the stage's song wheel both read what these produce from the API.

- Leading articles are ignored: "The Beatles" files under B, next to Beck.
- Accents fold to their base letter: "Édith Piaf" files under E.
- Anything that is not then a letter A–Z (digits, "*NSYNC") files under "#".
"""

import re
import unicodedata

_LEADING_ARTICLE = re.compile(r"^(the|a|an)\s+", re.IGNORECASE)


def filing_name(name: str) -> str:
    """Sort key for a name: article stripped, accents folded, case-folded."""
    stripped = _LEADING_ARTICLE.sub("", name.strip())
    # A name that is only an article ("The") keeps it rather than filing blank.
    stripped = stripped or name.strip()
    decomposed = unicodedata.normalize("NFKD", stripped)
    folded = "".join(c for c in decomposed if not unicodedata.combining(c))
    return folded.casefold()


def filing_letter(name: str) -> str:
    """The A–Z bucket a name files under, or "#" for anything else."""
    key = filing_name(name)
    first = key[:1].upper()
    return first if "A" <= first <= "Z" else "#"
