"""Tests for telling album track uploads from videos with a picture of their own."""

import pytest

from app.services.youtube_service import is_album_art_upload


@pytest.mark.parametrize(
    "info",
    [
        # yt-dlp's usual info: " - Topic" already dropped from the channel
        {
            "channel": "ABBA",
            "description": "Provided to YouTube by Universal Music Group\n\nTrack",
        },
        {"description": "\n  Provided to YouTube by The Orchard Enterprises"},
        {"channel": "Andrew Huang - Topic", "description": ""},
        {"uploader": "Andrew Huang - Topic"},
    ],
)
def test_album_track_uploads(info):
    assert is_album_art_upload(info) is True


@pytest.mark.parametrize(
    "info",
    [
        {"channel": "ABBA", "description": "Official video for Dancing Queen"},
        {"channel": "Topic Lyrics", "description": "lyrics video"},
        {"channel": None, "uploader": None, "description": None},
        {},
    ],
)
def test_videos_with_a_picture_of_their_own(info):
    assert is_album_art_upload(info) is False
