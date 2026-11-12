"""Tests for editing a song's artist credits through PATCH /api/songs/{id}."""

import pytest

from app.db.models import DbArtist, DbSong
from app.services.artist_parsing import ArtistCredit
from app.services.song_artist_service import set_song_credits

SONG_ID = "song-credits"


@pytest.fixture
def song(db):
    song = DbSong(
        id=SONG_ID,
        title="Baddadan",
        artist="Chase & Status feat. Popcaan & IRah",
        musicbrainz_recording_id="mbid-rec",
        acoustid_fingerprint_status="matched",
    )
    db.add(song)
    db.commit()
    set_song_credits(db, song, [ArtistCredit("Chase & Status")])
    db.commit()
    return song


def _credits(db):
    db.expire_all()
    song = db.get(DbSong, SONG_ID)
    return song, [
        (link.artist_rel.display_name, link.role)
        for link in sorted(song.song_artists, key=lambda link: link.display_order)
    ]


def test_a_credit_list_is_written_as_given(client, db, song):
    resp = client.patch(
        f"/api/songs/{SONG_ID}",
        json={
            "artists": [
                {"name": "Chase & Status", "role": "primary"},
                {"name": "Popcaan", "role": "featured"},
                {"name": "IRah", "role": "featured"},
            ]
        },
    )

    assert resp.status_code == 200
    song, credits = _credits(db)
    assert credits == [
        ("Chase & Status", "primary"),
        ("Popcaan", "featured"),
        ("IRah", "featured"),
    ]
    # The text is rebuilt from the list and the song confirmed; the recording stays
    assert song.artist == "Chase & Status feat. Popcaan, IRah"
    assert song.metadata_confirmed_at is not None
    assert song.musicbrainz_recording_id == "mbid-rec"
    assert [a["name"] for a in resp.json()["artists"]] == [
        "Chase & Status",
        "Popcaan",
        "IRah",
    ]


def test_the_list_wins_over_artist_text(client, db, song):
    client.patch(
        f"/api/songs/{SONG_ID}",
        json={"artist": "Somebody Else", "artists": [{"name": "A", "role": "primary"}]},
    )

    song, credits = _credits(db)
    assert song.artist == "A"
    assert credits == [("A", "primary")]


def test_a_list_needs_a_primary(client, db, song):
    resp = client.patch(
        f"/api/songs/{SONG_ID}",
        json={"artists": [{"name": "Popcaan", "role": "featured"}]},
    )

    assert resp.status_code == 422
    assert _credits(db)[1] == [("Chase & Status", "primary")]


def test_retyped_artist_text_is_parsed(client, db, song):
    client.patch(
        f"/api/songs/{SONG_ID}",
        json={"artist": "Chase & Status feat. Popcaan & IRah & Bou"},
    )

    song, credits = _credits(db)
    assert credits == [
        ("Chase & Status", "primary"),
        ("Popcaan", "featured"),
        ("IRah", "featured"),
        ("Bou", "featured"),
    ]
    assert song.metadata_confirmed_at is not None


def test_unchanged_artist_text_keeps_the_credits(client, db, song):
    client.patch(
        f"/api/songs/{SONG_ID}",
        json={"artist": "Chase & Status feat. Popcaan & IRah", "album": "X"},
    )

    assert _credits(db)[1] == [("Chase & Status", "primary")]
    assert db.query(DbArtist).count() == 1
