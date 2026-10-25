"""Tests for writing artist credits (set_song_credits) and resolving artists."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.db.models import DbAlbum, DbArtist, DbArtistAlias, DbSong, DbSongArtist
from app.jobs.metadata_tasks import enrich_song_artist_credits
from app.repositories.artist_repository import ArtistRepository
from app.services.artist_parsing import ArtistCredit
from app.services.song_artist_service import (
    parse_credits,
    set_song_credits,
    split_known_primaries,
)


@pytest.fixture
def db(test_db_session):
    return test_db_session


@pytest.fixture
def repo(db):
    return ArtistRepository(db)


def _song(db, song_id="s1", **fields):
    fields.setdefault("title", "Song")
    fields.setdefault("artist", "Artist")
    song = DbSong(id=song_id, **fields)
    db.add(song)
    db.commit()
    return song


def _credits(db, song_id="s1"):
    """[(display name, role, credited_as)] in display order."""
    db.expire_all()
    song = db.get(DbSong, song_id)
    return [
        (link.artist_rel.display_name, link.role, link.credited_as)
        for link in sorted(song.song_artists, key=lambda link: link.display_order)
    ]


# --- set_song_credits ---


def test_youtube_music_list_is_kept_as_given(db):
    song = _song(db, artist="Chase & Status feat. Popcaan, IRah")

    set_song_credits(
        db,
        song,
        [
            ArtistCredit("Chase & Status", "primary", youtube_music_id="UC-cs"),
            ArtistCredit("Popcaan", "featured", youtube_music_id="UC-pop"),
            ArtistCredit("IRah", "featured"),
        ],
    )
    db.commit()

    assert _credits(db) == [
        ("Chase & Status", "primary", "Chase & Status"),
        ("Popcaan", "featured", "Popcaan"),
        ("IRah", "featured", "IRah"),
    ]
    chase = db.query(DbArtist).filter_by(name="chase & status").one()
    assert chase.youtube_music_artist_id == "UC-cs"
    assert db.get(DbSong, "s1").artist_id == chase.id
    # The artist text is never rewritten
    assert db.get(DbSong, "s1").artist == "Chase & Status feat. Popcaan, IRah"


def test_none_parses_the_artist_text_and_title(db):
    song = _song(db, artist="Drake feat. Rihanna & Future", title="X (feat. Bou)")

    set_song_credits(db, song, None)
    db.commit()

    assert [(n, r) for n, r, _ in _credits(db)] == [
        ("Drake", "primary"),
        ("Rihanna", "featured"),
        ("Future", "featured"),
        ("Bou", "featured"),
    ]


def test_replacing_credits_keeps_shared_artists(db):
    song = _song(db)
    set_song_credits(db, song, [ArtistCredit("A"), ArtistCredit("B", "featured")])
    db.commit()

    set_song_credits(db, song, [ArtistCredit("B"), ArtistCredit("C", "featured")])
    db.commit()

    assert [(n, r) for n, r, _ in _credits(db)] == [
        ("B", "primary"),
        ("C", "featured"),
    ]


def test_a_list_without_a_primary_makes_the_first_primary(db):
    song = _song(db)
    set_song_credits(db, song, [ArtistCredit("A", "featured")])
    db.commit()
    assert _credits(db)[0][1] == "primary"


def test_an_artist_named_twice_is_credited_once(db):
    song = _song(db)
    set_song_credits(
        db, song, [ArtistCredit("Jay-Z"), ArtistCredit("Jay‐Z", "featured")]
    )
    db.commit()
    assert [(n, r) for n, r, _ in _credits(db)] == [("Jay-Z", "primary")]


def test_primaries_come_before_featured(db):
    song = _song(db)
    set_song_credits(
        db, song, [ArtistCredit("Guest", "featured"), ArtistCredit("Main")]
    )
    db.commit()
    assert [n for n, _, _ in _credits(db)] == ["Main", "Guest"]


# --- Recording credits and the confirmed lock ---


RECORDING = [
    ArtistCredit(
        "The Chicks", "primary", musicbrainz_id="mb-chicks", credited_as="Dixie Chicks"
    ),
    ArtistCredit("Guest", "featured", musicbrainz_id="mb-guest"),
]


@pytest.fixture
def recording_lookup():
    with patch(
        "app.services.musicbrainz_service.get_recording_details",
        return_value=(None, RECORDING),
    ) as lookup:
        yield lookup


def test_a_linked_recording_replaces_the_list(db, recording_lookup):
    song = _song(db, artist="Dixie Chicks", musicbrainz_recording_id="rec")
    set_song_credits(db, song, [ArtistCredit("Dixie Chicks")])
    db.commit()

    assert enrich_song_artist_credits("s1")["status"] == "ok"

    # The earlier "Dixie Chicks" row resolved by its credited name, so there's
    # one artist. It keeps its name: only the rebuild renames artists.
    assert _credits(db) == [
        ("Dixie Chicks", "primary", "Dixie Chicks"),
        ("Guest", "featured", "Guest"),
    ]
    artist = db.query(DbArtist).filter_by(musicbrainz_artist_id="mb-chicks").one()
    assert db.query(DbArtist).count() == 2
    assert db.get(DbSong, "s1").artist == "Dixie Chicks"
    assert artist.id == db.get(DbSong, "s1").artist_id


def test_a_confirmed_song_is_left_alone(db, recording_lookup):
    _song(
        db,
        artist="Dixie Chicks",
        musicbrainz_recording_id="rec",
        metadata_confirmed_at=datetime.now(timezone.utc),
    )
    set_song_credits(db, db.get(DbSong, "s1"), [ArtistCredit("Dixie Chicks")])
    db.commit()

    assert enrich_song_artist_credits("s1")["status"] == "confirmed"
    assert [n for n, _, _ in _credits(db)] == ["Dixie Chicks"]


def test_a_picked_recording_overrides_the_lock(db, recording_lookup):
    _song(
        db,
        musicbrainz_recording_id="rec",
        metadata_confirmed_at=datetime.now(timezone.utc),
    )

    assert enrich_song_artist_credits("s1", picked=True)["status"] == "ok"
    assert [n for n, _, _ in _credits(db)] == ["The Chicks", "Guest"]


def test_no_recording_credits_keeps_the_song_as_it_is(db):
    song = _song(db, musicbrainz_recording_id="rec")
    set_song_credits(db, song, [ArtistCredit("Kept")])
    db.commit()

    with patch(
        "app.services.musicbrainz_service.get_recording_details",
        return_value=(None, None),
    ):
        assert enrich_song_artist_credits("s1")["status"] == "no_credits"
    assert [n for n, _, _ in _credits(db)] == ["Kept"]


def test_a_song_without_a_recording_is_not_looked_up(db):
    _song(db)
    with patch("app.services.musicbrainz_service.get_recording_details") as lookup:
        assert enrich_song_artist_credits("s1")["status"] == "no_recording"
    lookup.assert_not_called()


# --- Resolving artists ---


def test_resolve_by_alias(db, repo):
    chicks = repo.resolve("The Chicks", "mb-chicks")
    repo.add_alias(chicks, "Dixie Chicks", "musicbrainz")

    assert repo.resolve("dixie chicks") == chicks
    assert repo.resolve("Dixie Chicks!") == chicks


def test_resolve_prefers_ids_over_names(db, repo):
    by_mbid = repo.resolve("Prince", "mb-prince")
    repo.resolve("Other Prince")

    assert repo.resolve("Other Prince", "mb-prince") == by_mbid


def test_resolve_by_youtube_music_id(db, repo):
    artist = repo.resolve("Bonobo", ytm_id="UC-bonobo")
    assert repo.resolve("Bonobo (Official)", ytm_id="UC-bonobo") == artist


def test_a_name_match_picks_up_the_credits_ids(db, repo):
    artist = repo.resolve("Bonobo")
    assert repo.resolve("Bonobo", "mb-bonobo", "UC-bonobo") == artist
    assert artist.musicbrainz_artist_id == "mb-bonobo"
    assert artist.youtube_music_artist_id == "UC-bonobo"


def test_resolve_upgrades_a_lowercase_display_name_but_not_a_hand_set_one(db, repo):
    weeknd = DbArtist(name="the weeknd", display_name="the weeknd")
    prince = DbArtist(name="prince", display_name="Prince & The Revolution")
    db.add_all([weeknd, prince])
    db.flush()

    assert repo.resolve("The Weeknd").display_name == "The Weeknd"
    assert repo.resolve("Prince").display_name == "Prince & The Revolution"


def test_resolve_matches_unicode_hyphens(db, repo):
    artist = repo.resolve("Jay-Z")
    assert repo.resolve("Jay‐Z") == artist


def test_split_known_primaries(db, repo):
    repo.resolve("Amber Mark")
    repo.resolve("John The Blind")
    repo.resolve("Chase & Status")
    repo.resolve("Bou")

    assert split_known_primaries("Amber Mark & John The Blind", db) == [
        "Amber Mark",
        "John The Blind",
    ]
    assert split_known_primaries("Chase & Status", db) == ["Chase & Status"]
    assert split_known_primaries("Chase & Status and Bou", db) == [
        "Chase & Status",
        "Bou",
    ]
    assert split_known_primaries("Amber Mark & Someone", db) == ["Amber Mark & Someone"]


def test_split_never_breaks_a_band_name(db, repo):
    repo.resolve("Bob Marley")
    repo.resolve("The Wailers")
    assert split_known_primaries("Bob Marley & The Wailers", db) == [
        "Bob Marley & The Wailers"
    ]


def test_parse_credits_adds_title_guests_as_featured(db):
    credits = parse_credits(db, "A feat. B", "Song (feat. C)")
    assert [(c.name, c.role) for c in credits] == [
        ("A", "primary"),
        ("B", "featured"),
        ("C", "featured"),
    ]


# --- Merging ---


def test_merge_moves_credits_songs_albums_and_names(db, repo):
    # Two rows for one artist, as older imports left them
    old = DbArtist(name="jay\u2010z", display_name="Jay\u2010Z")
    new = DbArtist(name="jay-z", display_name="JAY-Z", musicbrainz_artist_id="mb-jay")
    db.add_all([old, new])
    db.flush()
    db.add_all(
        [
            DbSong(id="solo", title="Solo", artist="Jay-Z", artist_id=old.id),
            DbSong(id="both", title="Both", artist="Jay-Z", artist_id=new.id),
            DbSongArtist(song_id="solo", artist_id=old.id, role="primary"),
            DbSongArtist(song_id="both", artist_id=old.id, role="primary"),
            DbSongArtist(song_id="both", artist_id=new.id, role="featured"),
            DbAlbum(source="deezer", source_id="1", title="Album", artist_id=old.id),
        ]
    )
    db.commit()

    assert repo.merge_into(old, new) == 2
    db.commit()

    assert db.get(DbArtist, old.id) is None
    links = db.query(DbSongArtist).filter_by(artist_id=new.id).all()
    # A song crediting both keeps one credit, primary over featured
    assert {(link.song_id, link.role) for link in links} == {
        ("solo", "primary"),
        ("both", "primary"),
    }
    assert db.get(DbSong, "solo").artist_id == new.id
    assert db.query(DbAlbum).one().artist_id == new.id
    # The old spelling is kept as an alias
    assert repo.find("Jay\u2010Z") == new
