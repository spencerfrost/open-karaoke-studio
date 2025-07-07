import random

import pytest
from app.db.models import DbSong


@pytest.fixture(scope="function")
def populate_test_songs(db_session):
    """
    Populate the test database with 25 representative songs for integration tests.
    Songs will have a mix of artists, albums, and special characters.
    """
    artists = ["Artist A", "Artist B", "Artist C", "Björk", "李荣浩"]
    albums = ["Hits 1", "Hits 2", "Classics", "Specials"]
    for i in range(25):
        song = DbSong(
            id=f"song-{i+1}",
            title=f"Test Song {i+1} {'★' if i % 5 == 0 else ''}",
            artist=random.choice(artists),
            album=random.choice(albums),
            duration_ms=180000 + i * 1000,
            date_added=None,
            vocals_path=f"/tmp/test_songs/vocals_{i+1}.wav",
            instrumental_path=f"/tmp/test_songs/instrumental_{i+1}.wav",
            original_path=f"/tmp/test_songs/original_{i+1}.wav",
            thumbnail_path=f"/tmp/test_songs/thumb_{i+1}.jpg",
            cover_art_path=f"/tmp/test_songs/cover_{i+1}.jpg",
            source="test",
            source_url=f"http://example.com/song/{i+1}",
            video_id=f"vid{i+1}",
            uploader="TestUploader",
            uploader_id="uploader123",
            channel="TestChannel",
            channel_id="channel123",
            description=f"Description for song {i+1}",
            upload_date=None,
            mbid=None,
            release_id=None,
            release_date=None,
            year=2020 + (i % 5),
            genre=random.choice(["Pop", "Rock", "Jazz", "Classical"]),
            language=random.choice(["English", "Spanish", "Chinese"]),
            lyrics="La la la...",
            synced_lyrics=None,
        )
        db_session.add(song)
    db_session.commit()
    yield
    db_session.query(DbSong).delete()
    db_session.commit()
