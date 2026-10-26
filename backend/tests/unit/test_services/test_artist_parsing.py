"""Tests for artist name parsing and MusicBrainz credit parsing."""

import pytest

from app.services.artist_parsing import (
    ArtistCredit,
    artist_credit,
    clean_artist_name,
    credit_line,
    normalize_artist_name,
    parse_song_artists,
    parse_title_featured,
)
from app.services.musicbrainz_service import _parse_artist_credits, artist_aliases_from


@pytest.mark.parametrize(
    "input_str, expected_primary, expected_featured",
    [
        ("Bonobo ft Fink", "Bonobo", ["Fink"]),
        ("Bonobo ft. Fink", "Bonobo", ["Fink"]),
        ("Bonobo feat Fink", "Bonobo", ["Fink"]),
        ("Bonobo feat. Fink", "Bonobo", ["Fink"]),
        ("Bonobo featuring Fink", "Bonobo", ["Fink"]),
        ("Bonobo feat. Fink, Joy", "Bonobo", ["Fink", "Joy"]),
        ("Bonobo FT Fink", "Bonobo", ["Fink"]),
        ("Simon & Garfunkel", "Simon & Garfunkel", []),
        ("Bonobo", "Bonobo", []),
        ("  Bonobo  ft  Fink  ", "Bonobo", ["Fink"]),
        ("Artist feat. One, Two, Three", "Artist", ["One", "Two", "Three"]),
        # Guests grouped with "&", "and" or "with" are separate artists
        ("Chase & Status feat. Popcaan & IRah", "Chase & Status", ["Popcaan", "IRah"]),
        ("A feat. B and C", "A", ["B", "C"]),
        ("A feat. B with C", "A", ["B", "C"]),
        ("A feat. B, C & D", "A", ["B", "C", "D"]),
        # ...unless the join is part of a band name
        ("A feat. Bob Marley & The Wailers", "A", ["Bob Marley & The Wailers"]),
        ("A feat. Florence and the Machine", "A", ["Florence and the Machine"]),
        # The primary side is never split here
        ("Chase & Status and Bou", "Chase & Status and Bou", []),
        # Unicode hyphens become plain ones
        ("Jay\u2010Z feat. Ne\u2011Yo", "Jay-Z", ["Ne-Yo"]),
    ],
)
def test_parse_song_artists(input_str, expected_primary, expected_featured):
    primary, featured = parse_song_artists(input_str)
    assert primary == expected_primary
    assert featured == expected_featured


# --- MusicBrainz artist credit parsing ---


def _mb(name, joinphrase="", *, credited=None, mbid=None):
    return {
        "name": credited or name,
        "artist": {"name": name, "id": mbid or f"mb-{name}"},
        "joinphrase": joinphrase,
    }


def _roles(credits):
    return [(c.name, c.role) for c in credits]


class TestParseArtistCredits:
    def test_empty_list(self):
        assert _parse_artist_credits([]) == []

    def test_single_artist(self):
        assert _roles(_parse_artist_credits([_mb("Bonobo")])) == [("Bonobo", "primary")]

    def test_ampersand_collaboration(self):
        """Two separate MB artist entities joined by '&' → two primaries."""
        credits = [_mb("Amber Mark", " & "), _mb("John the Blind")]
        assert _roles(_parse_artist_credits(credits)) == [
            ("Amber Mark", "primary"),
            ("John the Blind", "primary"),
        ]

    def test_band_name_single_entity(self):
        """A band name is a single MB entity — not split."""
        credits = [_mb("Bob Marley & The Wailers")]
        assert _roles(_parse_artist_credits(credits)) == [
            ("Bob Marley & The Wailers", "primary")
        ]

    def test_featured_via_joinphrase(self):
        """Artists after 'feat.' joinphrase are marked featured."""
        credits = [_mb("Bonobo", " feat. "), _mb("Fink")]
        assert _roles(_parse_artist_credits(credits)) == [
            ("Bonobo", "primary"),
            ("Fink", "featured"),
        ]

    def test_collab_plus_featured(self):
        """A & B feat. C → two primaries + one featured."""
        credits = [_mb("Artist A", " & "), _mb("Artist B", " feat. "), _mb("Artist C")]
        assert _roles(_parse_artist_credits(credits)) == [
            ("Artist A", "primary"),
            ("Artist B", "primary"),
            ("Artist C", "featured"),
        ]

    def test_multiple_featured(self):
        """Primary feat. A, B → one primary + two featured."""
        credits = [_mb("Main", " featuring "), _mb("Guest A", ", "), _mb("Guest B")]
        assert _roles(_parse_artist_credits(credits)) == [
            ("Main", "primary"),
            ("Guest A", "featured"),
            ("Guest B", "featured"),
        ]

    def test_keeps_id_current_name_and_credited_name(self):
        credits = [_mb("The Chicks", credited="Dixie Chicks", mbid="mb-chicks")]
        assert _parse_artist_credits(credits) == [
            ArtistCredit(
                name="The Chicks",
                role="primary",
                musicbrainz_id="mb-chicks",
                credited_as="Dixie Chicks",
            )
        ]

    def test_placeholder_artists_file_under_the_printed_name(self):
        credits = [
            _mb("Jesse L. Martin", " & "),
            _mb("[theatre]", "", credited="Cast of Rent", mbid="mb-theatre"),
        ]
        assert _parse_artist_credits(credits)[1] == ArtistCredit(
            name="Cast of Rent", role="primary", credited_as="Cast of Rent"
        )

    def test_placeholder_artists_printed_as_themselves_are_dropped(self):
        credits = [_mb("[unknown]"), _mb("Various Artists")]
        assert _parse_artist_credits(credits) == []

    def test_unicode_hyphens_become_plain(self):
        [credit] = _parse_artist_credits([_mb("Jay\u2010Z")])
        assert credit.name == "Jay-Z"
        assert credit.credited_as == "Jay-Z"


def test_artist_aliases_from_lists_name_and_aliases():
    data = {
        "name": "The Chicks",
        "aliases": [{"name": "Dixie Chicks"}, {"name": "The Dixie Chicks"}, {}],
    }
    assert artist_aliases_from(data) == [
        "The Chicks",
        "Dixie Chicks",
        "The Dixie Chicks",
    ]


# --- Title featuring ---


@pytest.mark.parametrize(
    "title, expected",
    [
        ("Pound Cake (feat. JAY-Z)", ["JAY-Z"]),
        ("Song [ft. A & B]", ["A", "B"]),
        ("Song (Featuring A, B)", ["A", "B"]),
        ("Song (Remix)", []),
        ("Feather", []),
        ("", []),
    ],
)
def test_parse_title_featured(title, expected):
    assert parse_title_featured(title) == expected


def test_clean_artist_name():
    assert clean_artist_name("  Jay\u2010Z   and  co ") == "Jay-Z and co"


# --- Artist name normalization ---


@pytest.mark.parametrize(
    "a, b",
    [
        ("Norah Jones", "norah jones"),
        ("Cee Lo Green", "CeeLo Green"),
        ("Beyoncé", "Beyonce"),
        ("Simon & Garfunkel", "Simon and Garfunkel"),
        ("The Beatles", "Beatles"),
        ("AC/DC", "ACDC"),
        ("P!nk", "Pnk"),
    ],
)
def test_normalize_artist_name_matches_variants(a, b):
    assert normalize_artist_name(a) == normalize_artist_name(b)


def test_normalize_artist_name_distinguishes_artists():
    assert normalize_artist_name("Norah Jones") != normalize_artist_name(
        "Kent Nishimura"
    )


def test_normalize_artist_name_matches_hyphen_and_and_spellings():
    assert normalize_artist_name("Jay\u2010Z") == normalize_artist_name("Jay-Z")
    assert normalize_artist_name(
        "Nahko And Medicine For The People"
    ) == normalize_artist_name("Nahko & Medicine for the People")


def test_normalize_artist_name_keeps_non_latin_letters():
    assert normalize_artist_name("宇多田ヒカル") != ""


@pytest.mark.parametrize(
    "names, expected",
    [
        (["Queen"], "Queen"),
        (["JAY-Z", "Alicia Keys"], "JAY-Z feat. Alicia Keys"),
        (["A", "B", "C"], "A feat. B, C"),
        ([" Queen ", ""], "Queen"),
        ([], ""),
    ],
)
def test_artist_credit(names, expected):
    assert artist_credit(names) == expected


def test_artist_credit_parses_back_to_the_same_artists():
    primary, featured = parse_song_artists(artist_credit(["JAY-Z", "Alicia Keys", "X"]))
    assert (primary, featured) == ("JAY-Z", ["Alicia Keys", "X"])


@pytest.mark.parametrize(
    "credits, expected",
    [
        ([("Queen", "primary")], "Queen"),
        ([("A", "primary"), ("B", "primary")], "A & B"),
        ([("A", "primary"), ("B", "primary"), ("C", "featured")], "A & B feat. C"),
        ([("A", "primary"), ("C", "featured"), ("D", "featured")], "A feat. C, D"),
        ([], ""),
    ],
)
def test_credit_line(credits, expected):
    assert credit_line(credits) == expected
