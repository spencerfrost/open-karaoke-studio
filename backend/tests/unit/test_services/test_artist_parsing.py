"""Tests for artist name parsing and credit resolution."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.artist_parsing import (
    artist_credit,
    normalize_artist_name,
    parse_song_artists,
)
from app.services.credits_resolver import resolve_artist_credits
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
            {
                "name": "Amber Mark",
                "artist": {"name": "Amber Mark"},
                "joinphrase": " & ",
            },
            {
                "name": "John The Blind",
                "artist": {"name": "John the Blind"},
                "joinphrase": "",
            },
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
            {
                "name": "Artist B",
                "artist": {"name": "Artist B"},
                "joinphrase": " feat. ",
            },
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


def test_normalize_artist_name_keeps_non_latin_letters():
    assert normalize_artist_name("宇多田ヒカル") != ""


# --- Credit resolution (MB search step) ---


def _search_result(score: float, credits: list[tuple[str, str]]) -> dict:
    return {"score": score, "recordingId": "rec-id", "artistCredits": credits}


class TestResolveArtistCredits:
    @pytest.fixture
    def mock_search(self):
        with patch("app.services.musicbrainz_service.search_recordings") as mock:
            yield mock

    def test_rejects_top_hit_by_another_artist(self, mock_search):
        """A cover whose title contains the real artist's name must not win."""
        mock_search.return_value = [
            _search_result(1.0, [("Kent Nishimura", "primary")]),
            _search_result(0.52, [("Norah Jones", "primary")]),
        ]
        with patch("app.services.credits_resolver.logger") as mock_logger:
            credits = resolve_artist_credits(
                "Norah Jones - Don't Know Why", "Norah Jones"
            )
        assert credits == [("Norah Jones", "primary")]
        assert any(
            "Rejected MB search result" in call.args[0]
            for call in mock_logger.info.call_args_list
        )

    def test_accepts_matching_artist(self, mock_search):
        mock_search.return_value = [
            _search_result(1.0, [("Bonobo", "primary"), ("Fink", "featured")]),
        ]
        credits = resolve_artist_credits("Kerala", "Bonobo")
        assert credits == [("Bonobo", "primary"), ("Fink", "featured")]

    def test_accepts_spelling_variant(self, mock_search):
        mock_search.return_value = [
            _search_result(0.95, [("CeeLo Green", "primary")]),
        ]
        credits = resolve_artist_credits("Crazy", "Cee Lo Green")
        assert credits == [("CeeLo Green", "primary")]

    def test_accepts_later_result_that_matches(self, mock_search):
        mock_search.return_value = [
            _search_result(1.0, [("Kent Nishimura", "primary")]),
            _search_result(0.92, [("Norah Jones", "primary"), ("Guest", "featured")]),
        ]
        credits = resolve_artist_credits("Don't Know Why", "Norah Jones")
        assert credits == [("Norah Jones", "primary"), ("Guest", "featured")]

    def test_matching_artist_below_threshold_falls_back(self, mock_search):
        mock_search.return_value = [
            _search_result(0.85, [("Norah Jones", "primary"), ("Guest", "featured")]),
        ]
        credits = resolve_artist_credits("Don't Know Why", "Norah Jones")
        assert credits == [("Norah Jones", "primary")]

    def test_accepts_collaboration_split_into_two_primaries(self, mock_search):
        """Song saved as "A & B"; MB credits A and B as separate artists."""
        mock_search.return_value = [
            _search_result(
                0.97, [("Amber Mark", "primary"), ("John The Blind", "primary")]
            ),
        ]
        credits = resolve_artist_credits("Some Song", "Amber Mark & John The Blind")
        assert credits == [("Amber Mark", "primary"), ("John The Blind", "primary")]

    def test_recording_credits_skip_search(self, mock_search):
        recording = [("Kent Nishimura", "primary")]
        assert resolve_artist_credits("x", "Norah Jones", recording) == recording
        mock_search.assert_not_called()

    def test_search_error_falls_back_to_regex(self, mock_search):
        mock_search.side_effect = RuntimeError("boom")
        credits = resolve_artist_credits("Kerala", "Bonobo feat. Fink")
        assert credits == [("Bonobo", "primary"), ("Fink", "featured")]


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
