"""Tests for artist name parsing and credit resolution."""

from unittest.mock import MagicMock

import pytest

from app.services.artist_parsing import parse_song_artists
from app.services.musicbrainz_service import _parse_artist_credits
from app.services.song_artist_service import try_ampersand_split


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
    ],
)
def test_parse_song_artists(input_str, expected_primary, expected_featured):
    primary, featured = parse_song_artists(input_str)
    assert primary == expected_primary
    assert featured == expected_featured


# --- MusicBrainz artist credit parsing ---


class TestParseArtistCredits:
    def test_empty_list(self):
        assert _parse_artist_credits([]) == []

    def test_single_artist(self):
        credits = [{"name": "Bonobo", "artist": {"name": "Bonobo"}, "joinphrase": ""}]
        assert _parse_artist_credits(credits) == [("Bonobo", "primary")]

    def test_ampersand_collaboration(self):
        """Two separate MB artist entities joined by '&' → two primaries."""
        credits = [
            {"name": "Amber Mark", "artist": {"name": "Amber Mark"}, "joinphrase": " & "},
            {"name": "John The Blind", "artist": {"name": "John the Blind"}, "joinphrase": ""},
        ]
        result = _parse_artist_credits(credits)
        assert result == [("Amber Mark", "primary"), ("John The Blind", "primary")]

    def test_band_name_single_entity(self):
        """A band name is a single MB entity — not split."""
        credits = [
            {
                "name": "Bob Marley & The Wailers",
                "artist": {"name": "Bob Marley & The Wailers"},
                "joinphrase": "",
            }
        ]
        result = _parse_artist_credits(credits)
        assert result == [("Bob Marley & The Wailers", "primary")]

    def test_featured_via_joinphrase(self):
        """Artists after 'feat.' joinphrase are marked featured."""
        credits = [
            {"name": "Bonobo", "artist": {"name": "Bonobo"}, "joinphrase": " feat. "},
            {"name": "Fink", "artist": {"name": "Fink"}, "joinphrase": ""},
        ]
        result = _parse_artist_credits(credits)
        assert result == [("Bonobo", "primary"), ("Fink", "featured")]

    def test_collab_plus_featured(self):
        """A & B feat. C → two primaries + one featured."""
        credits = [
            {"name": "Artist A", "artist": {"name": "Artist A"}, "joinphrase": " & "},
            {"name": "Artist B", "artist": {"name": "Artist B"}, "joinphrase": " feat. "},
            {"name": "Artist C", "artist": {"name": "Artist C"}, "joinphrase": ""},
        ]
        result = _parse_artist_credits(credits)
        assert result == [
            ("Artist A", "primary"),
            ("Artist B", "primary"),
            ("Artist C", "featured"),
        ]

    def test_multiple_featured(self):
        """Primary feat. A, B → one primary + two featured."""
        credits = [
            {"name": "Main", "artist": {"name": "Main"}, "joinphrase": " featuring "},
            {"name": "Guest A", "artist": {"name": "Guest A"}, "joinphrase": ", "},
            {"name": "Guest B", "artist": {"name": "Guest B"}, "joinphrase": ""},
        ]
        result = _parse_artist_credits(credits)
        assert result == [
            ("Main", "primary"),
            ("Guest A", "featured"),
            ("Guest B", "featured"),
        ]


# --- Heuristic ampersand splitting ---


def _mock_db_with_artists(*known_names: str):
    """Create a mock DB session where get_by_name returns truthy for known_names."""
    known = {n.lower().strip() for n in known_names}

    db = MagicMock()

    # Mock the query chain: db.query(...).filter(...).first()
    def mock_query_side_effect(*args):
        chain = MagicMock()

        def mock_filter(*filter_args):
            inner = MagicMock()

            def mock_first():
                # Extract the name from the filter expression
                # We check the bound parameters of the filter
                for arg in filter_args:
                    if hasattr(arg, "right") and hasattr(arg.right, "value"):
                        val = arg.right.value
                        if val in known:
                            return MagicMock()  # truthy — artist exists
                return None

            inner.first = mock_first
            return inner

        chain.filter = mock_filter
        return chain

    db.query = mock_query_side_effect
    return db


class TestTryAmpersandSplit:
    def test_no_ampersand_unchanged(self):
        credits = [("Bonobo", "primary")]
        db = MagicMock()
        assert try_ampersand_split(credits, db) == credits

    def test_already_split_unchanged(self):
        credits = [("Artist A", "primary"), ("Artist B", "primary")]
        db = MagicMock()
        assert try_ampersand_split(credits, db) == credits

    def test_band_name_pattern_not_split(self):
        """'& The' pattern should NOT be split."""
        credits = [("Bob Marley & The Wailers", "primary")]
        db = MagicMock()
        assert try_ampersand_split(credits, db) == credits

    def test_splits_when_both_known(self):
        """Splits when both parts exist as known artists."""
        credits = [("Amber Mark & John The Blind", "primary")]
        db = _mock_db_with_artists("amber mark", "john the blind")
        result = try_ampersand_split(credits, db)
        assert result == [("Amber Mark", "primary"), ("John The Blind", "primary")]

    def test_no_split_when_one_unknown(self):
        """Doesn't split when only one side is a known artist."""
        credits = [("Amber Mark & Some Unknown", "primary")]
        db = _mock_db_with_artists("amber mark")
        assert try_ampersand_split(credits, db) == credits

    def test_preserves_featured_on_split(self):
        """Featured artists are preserved after a split."""
        credits = [
            ("Amber Mark & John The Blind", "primary"),
            ("Guest", "featured"),
        ]
        db = _mock_db_with_artists("amber mark", "john the blind")
        result = try_ampersand_split(credits, db)
        assert result == [
            ("Amber Mark", "primary"),
            ("John The Blind", "primary"),
            ("Guest", "featured"),
        ]

    def test_his_her_their_pattern_not_split(self):
        """'& His/Her/Their' patterns should NOT be split."""
        for band in ["Jack & His Band", "Jill & Her Orchestra", "They & Their Crew"]:
            credits = [(band, "primary")]
            db = MagicMock()
            assert try_ampersand_split(credits, db) == credits
