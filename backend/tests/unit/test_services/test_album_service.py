"""Tests for finding a song's album: the YouTube Music lookup and Deezer's match rules."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
import requests
from ytmusicapi.exceptions import YTMusicServerError

from app.services import album_service
from app.services.album_service import (
    AlbumLookupError,
    AlbumMatch,
    deezer_result_matches,
    find_album,
)

ART = "https://yt3.googleusercontent.com/abc=w{0}-h{0}-l90-rj"


def _song(title="Sweet Emotion", artist="Aerosmith", video_id="vid1", credits=()):
    return SimpleNamespace(
        title=title,
        artist=artist,
        video_id=video_id,
        song_artists=[
            SimpleNamespace(
                role=role,
                display_order=i,
                artist_rel=SimpleNamespace(name=name.lower(), display_name=name),
            )
            for i, (name, role) in enumerate(credits)
        ],
    )


def _watch_track(video_id="vid1", album=("Toys In The Attic", "MPREb_1"), year="1975"):
    return {
        "videoId": video_id,
        "title": "Sweet Emotion",
        "album": {"name": album[0], "id": album[1]} if album else None,
        "year": year,
        "thumbnail": [{"url": ART.format(60)}, {"url": ART.format(544)}],
    }


def _ytmusic(tracks=None, search=(), watch_error=None):
    ytmusic = Mock()
    if watch_error:
        ytmusic.get_watch_playlist.side_effect = watch_error
    else:
        ytmusic.get_watch_playlist.return_value = {"tracks": tracks or []}
    ytmusic.search.return_value = list(search)
    return patch.object(album_service, "_youtube_music", return_value=ytmusic)


def _deezer_item(
    title="Sweet Emotion",
    artist="Aerosmith",
    album="Toys In The Attic",
    album_id=302,
    title_short=None,
    title_version="",
    explicit=False,
):
    return {
        "title": title,
        "title_short": title_short or title,
        "title_version": title_version,
        "explicit_lyrics": explicit,
        "artist": {"name": artist},
        "album": {
            "id": album_id,
            "title": album,
            "cover_xl": f"https://cdn-images.dzcdn.net/images/cover/ab{album_id}/1000x1000-000000-80-0-0.jpg",
        },
    }


def _deezer(*items, release_date="1975-04-08"):
    """Patch requests.get to answer the search with `items` and album lookups with a date."""

    def get(url, params=None, timeout=None):
        response = Mock()
        response.raise_for_status.return_value = None
        if url.endswith("/search"):
            response.json.return_value = {"data": list(items)}
        else:
            response.json.return_value = {"release_date": release_date}
        return response

    return patch.object(album_service.requests, "get", side_effect=get)


class TestYouTubeMusic:
    def test_uses_the_album_of_the_exact_video(self):
        search = [
            {"videoId": "other", "isExplicit": False},
            {"videoId": "vid1", "isExplicit": True},
        ]
        with _ytmusic([_watch_track()], search=search):
            match = find_album(_song())

        assert match == AlbumMatch(
            source="ytmusic",
            source_id="MPREb_1",
            title="Toys In The Attic",
            year="1975",
            cover_url="https://yt3.googleusercontent.com/abc=w1200-h1200-s-l90-rj",
            explicit=True,
        )

    def test_explicit_is_unknown_when_search_misses_the_video(self):
        with _ytmusic([_watch_track()], search=[{"videoId": "other"}]):
            match = find_album(_song())

        assert match.source == "ytmusic"
        assert match.explicit is None

    def test_a_video_on_no_album_falls_through_to_deezer(self):
        # Music videos and plain uploads come back without an album.
        with _ytmusic([_watch_track(album=None)]), _deezer(_deezer_item()):
            match = find_album(_song())

        assert match.source == "deezer"
        assert match.source_id == "302"
        assert match.year == "1975"

    def test_a_watch_page_for_another_video_is_ignored(self):
        with _ytmusic([_watch_track(video_id="else")]), _deezer():
            assert find_album(_song()) is None

    def test_a_removed_video_falls_through_to_deezer(self):
        gone = YTMusicServerError("No content returned by the server.")
        with _ytmusic(watch_error=gone), _deezer(_deezer_item()):
            assert find_album(_song()).source == "deezer"

    def test_an_unreachable_youtube_music_is_an_error_not_a_miss(self):
        with _ytmusic(watch_error=requests.ConnectionError("down")):
            with pytest.raises(AlbumLookupError):
                find_album(_song())

    def test_a_song_without_a_video_goes_straight_to_deezer(self):
        with _ytmusic() as ytmusic, _deezer(_deezer_item()):
            assert find_album(_song(video_id=None)).source == "deezer"
        ytmusic.assert_not_called()


class TestDeezer:
    def test_takes_the_first_result_that_matches(self):
        items = [
            _deezer_item(artist="Studio Group", album="Karaoke Hits", album_id=1),
            _deezer_item(album_id=302, explicit=True),
            _deezer_item(album="Big Ones", album_id=3),
        ]
        with _deezer(*items):
            match = find_album(_song(video_id=None))

        assert match.source_id == "302"
        assert match.explicit is True
        assert match.cover_url.endswith("/ab302/1000x1000-000000-80-0-0.jpg")

    def test_searches_by_the_primary_credit(self):
        song = _song(
            title="Stay",
            artist="The Kid LAROI & Justin Bieber",
            video_id=None,
            credits=[("Justin Bieber", "featured"), ("The Kid LAROI", "primary")],
        )
        item = _deezer_item(title="Stay", artist="The Kid LAROI")
        with _deezer(item) as get:
            assert find_album(song) is not None

        assert get.call_args_list[0].kwargs["params"]["q"] == "The Kid LAROI Stay"

    def test_nothing_matching_is_none(self):
        with _deezer(_deezer_item(artist="Someone Else")):
            assert find_album(_song(video_id=None)) is None

    def test_an_album_without_art_has_no_cover(self):
        item = _deezer_item()
        item["album"][
            "cover_xl"
        ] = "https://cdn-images.dzcdn.net/images/cover//1000x1000-000000-80-0-0.jpg"
        with _deezer(item):
            assert find_album(_song(video_id=None)).cover_url is None

    def test_a_quota_error_is_an_error_not_a_miss(self):
        response = Mock()
        response.json.return_value = {"error": {"code": 4, "message": "Quota"}}
        with patch.object(album_service.requests, "get", return_value=response):
            with pytest.raises(AlbumLookupError):
                find_album(_song(video_id=None))


def _matches(item, title="Sweet Emotion", artist="Aerosmith"):
    return deezer_result_matches(item, title=title, artist=artist)


class TestDeezerMatchRules:
    def test_same_artist_and_title_match(self):
        assert _matches(_deezer_item())

    def test_case_accents_and_punctuation_are_ignored(self):
        item = _deezer_item(title="Beyonce", artist="Beyoncé")
        assert _matches(item, title="Beyoncé", artist="BEYONCE")

    def test_a_leading_the_and_ampersand_are_ignored(self):
        item = _deezer_item(title="Mrs Robinson", artist="Simon & Garfunkel")
        assert _matches(item, title="Mrs. Robinson", artist="Simon and Garfunkel")
        item = _deezer_item(title="Let It Be", artist="Beatles")
        assert _matches(item, title="Let It Be", artist="The Beatles")

    def test_another_artist_doesnt_match(self):
        # The karaoke "Studio Group" recording of Colors of the Wind.
        item = _deezer_item(title="Colors of the Wind", artist="Studio Group")
        assert not _matches(item, title="Colors of the Wind", artist="Judy Kuhn")

    def test_featured_artists_are_dropped_from_both_sides(self):
        item = _deezer_item(title="Stay (feat. Justin Bieber)", artist="The Kid LAROI")
        assert _matches(item, title="Stay", artist="The Kid LAROI feat. Justin Bieber")
        assert _matches(item, title="Stay ft. Justin Bieber", artist="The Kid LAROI")
        item = _deezer_item(title="Glimpse of Us", artist="Joji")
        assert _matches(item, title="Glimpse of Us", artist="Joji with Someone")

    def test_with_in_a_title_is_part_of_the_title(self):
        item = _deezer_item(title="Stuck with U", artist="Ariana Grande")
        assert not _matches(item, title="Stuck", artist="Ariana Grande")

    def test_another_title_doesnt_match(self):
        assert not _matches(_deezer_item(title="Dream On"))

    def test_a_remaster_note_doesnt_stop_a_match(self):
        item = _deezer_item(
            title="Sweet Emotion (Remastered 2023)",
            title_short="Sweet Emotion",
            title_version="(Remastered 2023)",
        )
        assert _matches(item)

    def test_a_live_song_needs_a_live_result(self):
        studio = _deezer_item(title="Landslide", artist="Fleetwood Mac")
        live = _deezer_item(
            title="Landslide (Live 1977)",
            title_short="Landslide",
            title_version="(Live 1977)",
            artist="Fleetwood Mac",
        )
        assert not _matches(studio, title="Landslide (Live)", artist="Fleetwood Mac")
        assert _matches(live, title="Landslide (Live)", artist="Fleetwood Mac")

    def test_a_studio_song_doesnt_take_a_live_or_acoustic_result(self):
        for version in ("(Live 1977)", "(Acoustic)", "(Demo)", "(Remix)"):
            item = _deezer_item(
                title=f"Landslide {version}",
                title_short="Landslide",
                title_version=version,
                artist="Fleetwood Mac",
            )
            assert not _matches(item, title="Landslide", artist="Fleetwood Mac")

    def test_a_radio_edit_is_the_same_recording(self):
        item = _deezer_item(
            title="Sweet Emotion (Radio Edit)",
            title_short="Sweet Emotion",
            title_version="(Radio Edit)",
        )
        assert _matches(item)

    @pytest.mark.parametrize(
        "album",
        [
            "Karaoke Classics",
            "A Tribute to Aerosmith",
            "Hits Made Famous by Aerosmith",
            "In the Style of Aerosmith",
            "Rock Instrumentals",
            "The 8-Bit Aerosmith",
        ],
    )
    def test_cover_and_karaoke_albums_are_rejected(self, album):
        assert not _matches(_deezer_item(album=album))
