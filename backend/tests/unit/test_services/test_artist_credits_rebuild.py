"""Tests for the artist credits rebuild (app/services/artist_credits_rebuild.py)."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.db.models import BatchRun, DbAlbum, DbArtist, DbSong, DbSongArtist
from app.jobs.batch_tasks import batch_rebuild_artist_credits
from app.services.artist_credits_rebuild import (
    MusicBrainzData,
    credits_match_text,
    fetch_musicbrainz,
    library_numbers,
    rebuild,
)
from app.services.artist_parsing import ArtistCredit


@pytest.fixture
def db(test_db_session):
    return test_db_session


def _artist(db, display_name, **fields):
    artist = DbArtist(name=display_name.lower(), display_name=display_name, **fields)
    db.add(artist)
    db.flush()
    return artist


def _old_song(db, song_id, artist_text, *credits, title=None, **fields):
    """A song as the old code left it: credits without a credited name."""
    db.add(
        DbSong(
            id=song_id,
            title=title or song_id,
            artist=artist_text,
            artist_id=credits[0][0].id if credits else None,
            **fields,
        )
    )
    for order, (artist, role) in enumerate(credits):
        db.add(
            DbSongArtist(
                song_id=song_id, artist_id=artist.id, role=role, display_order=order
            )
        )
    db.flush()


def _credits(db, song_id):
    song = db.get(DbSong, song_id)
    return [
        (link.artist_rel.display_name, link.role)
        for link in sorted(song.song_artists, key=lambda link: link.display_order)
    ]


def test_recording_credits_replace_old_ones_even_on_confirmed_songs(db):
    grouped = _artist(db, "Popcaan & IRah")
    chase = _artist(db, "Chase & Status")
    _old_song(
        db,
        "baddadan",
        "Chase & Status feat. Popcaan & IRah",
        (chase, "primary"),
        (grouped, "featured"),
        musicbrainz_recording_id="rec",
        metadata_confirmed_at=datetime.now(timezone.utc),
    )
    mb = MusicBrainzData(
        recordings={
            "rec": [
                ArtistCredit("Chase & Status", musicbrainz_id="mb-cs"),
                ArtistCredit("Popcaan", "featured", musicbrainz_id="mb-pop"),
                ArtistCredit("IRah", "featured", musicbrainz_id="mb-irah"),
            ]
        }
    )

    report = rebuild(db, mb)

    assert _credits(db, "baddadan") == [
        ("Chase & Status", "primary"),
        ("Popcaan", "featured"),
        ("IRah", "featured"),
    ]
    [changed] = report["songs"]["changed"]
    assert changed["confirmed"] is True
    assert changed["source"] == "recording"
    # The grouped guest has nothing left and goes
    assert report["deleted"]["names"] == ["Popcaan & IRah"]
    assert db.get(DbSong, "baddadan").artist == "Chase & Status feat. Popcaan & IRah"


def test_songs_without_a_recording_are_reparsed_once(db):
    grouped = _artist(db, "Popcaan & IRah")
    main = _artist(db, "Chase & Status")
    _old_song(
        db,
        "old",
        "Chase & Status feat. Popcaan & IRah",
        (main, "primary"),
        (grouped, "featured"),
    )

    rebuild(db, MusicBrainzData())
    assert _credits(db, "old") == [
        ("Chase & Status", "primary"),
        ("Popcaan", "featured"),
        ("IRah", "featured"),
    ]

    # A second run finds them credited from a list and leaves them
    report = rebuild(db, MusicBrainzData())
    assert report["songs"]["counts"] == {"kept": 1}


def test_merges_spellings_and_mb_aliases(db):
    hyphen = _artist(db, "Jay‐Z")
    plain = _artist(db, "Jay-Z")
    chicks = _artist(db, "The Chicks", musicbrainz_artist_id="mb-chicks")
    dixie = _artist(db, "Dixie Chicks")
    _old_song(db, "a", "Jay-Z", (hyphen, "primary"))
    _old_song(db, "b", "Jay-Z", (plain, "primary"))
    _old_song(db, "c", "Jay-Z", (plain, "primary"))
    _old_song(db, "d", "Dixie Chicks", (dixie, "primary"))
    db.add(DbAlbum(source="deezer", source_id="1", title="Fly", artist_id=dixie.id))
    db.flush()
    mb = MusicBrainzData(artists={"mb-chicks": ["The Chicks", "Dixie Chicks"]})

    report = rebuild(db, mb)

    merges = {(m["from"], m["into"], m["reason"]) for m in report["merges"]}
    assert ("Dixie Chicks", "The Chicks", "musicbrainz") in merges
    # The spelling most songs use stays
    assert ("Jay‐Z", "Jay-Z", "spelling") in merges or (
        "Jay-Z",
        "Jay-Z",
        "spelling",
    ) in merges
    assert db.query(DbArtist).filter(DbArtist.display_name.like("Jay%")).count() == 1
    assert _credits(db, "d") == [("The Chicks", "primary")]
    assert db.query(DbAlbum).one().artist_id == chicks.id


def test_names_from_musicbrainz_and_printed_case(db):
    weeknd = _artist(db, "the weeknd")
    chicks = _artist(db, "Dixie Chicks", musicbrainz_artist_id="mb-chicks")
    db.add(DbSong(id="s", title="S", artist="The Weeknd", artist_id=weeknd.id))
    db.add(
        DbSongArtist(
            song_id="s", artist_id=weeknd.id, role="primary", credited_as="The Weeknd"
        )
    )
    db.flush()
    mb = MusicBrainzData(artists={"mb-chicks": ["The Chicks"]})

    report = rebuild(db, mb)

    assert {(r["from"], r["to"]) for r in report["renames"]} == {
        ("the weeknd", "The Weeknd"),
        ("Dixie Chicks", "The Chicks"),
    }
    assert chicks.display_name == "The Chicks"
    assert chicks.name == "the chicks"


def test_different_mb_artists_never_merge(db):
    _artist(db, "Nirvana", musicbrainz_artist_id="mb-us")
    db.add(
        DbArtist(
            name="nirvana (uk)", display_name="Nirvana", musicbrainz_artist_id="mb-uk"
        )
    )
    db.flush()

    report = rebuild(db, MusicBrainzData())

    assert report["merges"] == []


def test_report_lists_unsure_and_disagreeing_songs(db):
    pair = _artist(db, "Amber Mark & John The Blind")
    other = _artist(db, "John The Blind")
    _old_song(db, "unsure", "Amber Mark & John The Blind", (pair, "primary"))
    db.add(DbSong(id="wrong", title="W", artist="Amber Mark", artist_id=other.id))
    db.add(
        DbSongArtist(
            song_id="wrong",
            artist_id=other.id,
            role="primary",
            credited_as="John The Blind",
        )
    )
    db.flush()

    report = rebuild(db, MusicBrainzData())

    assert [s["songId"] for s in report["unsure"]["songs"]] == ["unsure"]
    assert [s["songId"] for s in report["disagree"]["songs"]] == ["wrong"]


def test_credits_match_text_accepts_joined_primaries(db):
    amber = _artist(db, "Amber Mark")
    john = _artist(db, "John The Blind")
    db.add(DbSong(id="s", title="S", artist="Amber Mark & John The Blind"))
    db.add_all(
        [
            DbSongArtist(song_id="s", artist_id=amber.id, role="primary"),
            DbSongArtist(
                song_id="s", artist_id=john.id, role="primary", display_order=1
            ),
        ]
    )
    db.flush()
    assert credits_match_text(db.get(DbSong, "s"))


def test_library_numbers(db):
    bonobo = _artist(db, "Bonobo")
    grey = _artist(db, "Grey Reverend")
    _artist(db, "Nobody")
    _old_song(
        db,
        "s",
        "Bonobo feat. Grey Reverend",
        (bonobo, "primary"),
        (grey, "featured"),
        title="Song (feat. Grey Reverend)",
    )

    numbers = library_numbers(db)

    assert numbers["songs"] == 1
    assert numbers["artistsLinked"] == 2
    assert numbers["artistsLinkedToNothing"] == 1
    assert numbers["featuredOnly"] == 1
    assert numbers["featuredOnlyOnOneSong"] == 1
    assert numbers["featInTitle"] == 1


def test_fetch_looks_up_each_recording_and_artist_once(db, tmp_path):
    db.add_all(
        [
            DbSong(id="a", title="A", artist="X", musicbrainz_recording_id="rec"),
            DbSong(id="b", title="B", artist="X", musicbrainz_recording_id="rec"),
            DbSong(id="c", title="C", artist="X"),
        ]
    )
    db.commit()
    steps = []

    with (
        patch(
            "app.services.musicbrainz_service.get_recording_details",
            return_value=(None, [ArtistCredit("X", musicbrainz_id="mb-x")]),
        ) as recording,
        patch(
            "app.services.musicbrainz_service.get_artist_aliases",
            return_value=["X", "Ex"],
        ) as aliases,
    ):
        data = fetch_musicbrainz(
            db, tmp_path, on_total=steps.append, on_step=lambda: steps.append(".")
        )

    recording.assert_called_once_with("rec", tmp_path)
    aliases.assert_called_once_with("mb-x", tmp_path)
    assert data.artists == {"mb-x": ["X", "Ex"]}
    assert steps == [3, ".", ".", ".", 4, "."]


class TestTask:
    @pytest.fixture
    def library(self, db):
        grouped = _artist(db, "Popcaan & IRah")
        main = _artist(db, "Chase & Status")
        _old_song(
            db,
            "old",
            "Chase & Status feat. Popcaan & IRah",
            (main, "primary"),
            (grouped, "featured"),
        )
        run = BatchRun(kind="artist_credits", mode="preview", status="queued")
        db.add(run)
        db.commit()
        return run.id

    def test_preview_changes_nothing_and_saves_the_report(self, db, library):
        result = batch_rebuild_artist_credits(mode="preview", run_id=library)

        assert result["songs_changed"] == 1
        db.expire_all()
        assert _credits(db, "old") == [
            ("Chase & Status", "primary"),
            ("Popcaan & IRah", "featured"),
        ]
        run = db.get(BatchRun, library)
        assert run.status == "done"
        assert run.report["mode"] == "preview"
        assert run.report["songs"]["counts"]["changed"] == 1

    def test_apply_commits(self, db, library):
        batch_rebuild_artist_credits(mode="apply", run_id=library)

        db.expire_all()
        assert _credits(db, "old") == [
            ("Chase & Status", "primary"),
            ("Popcaan", "featured"),
            ("IRah", "featured"),
        ]
