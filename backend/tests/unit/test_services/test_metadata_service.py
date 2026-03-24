"""Unit tests for MetadataService."""
from unittest.mock import patch

import pytest

from app.services.metadata_service import MetadataService


@pytest.fixture
def service():
    return MetadataService()


SAMPLE_ITUNES_RESULT = {
    "id": "12345",
    "title": "Never Gonna Give You Up",
    "artist": "Rick Astley",
    "album": "Whenever You Need Somebody",
    "releaseDateFormatted": "1987-11-01",
    "releaseYear": 1987,
    "genre": "Pop",
    "trackNumber": 1,
    "previewUrl": "https://example.com/preview.mp3",
    "trackExplicitness": "notExplicit",
    "isStreamable": True,
    "artistId": 987,
    "albumId": 654,
    "discNumber": 1,
    "country": "USA",
    "price": 1.29,
}


class TestSearchMetadata:
    def test_delegates_to_itunes_service(self, service):
        with patch("app.services.metadata_service.search_itunes") as mock_search:
            mock_search.return_value = [SAMPLE_ITUNES_RESULT]
            results = service.search_metadata("Rick Astley", "Never Gonna Give You Up")
        mock_search.assert_called_once_with("Rick Astley", "Never Gonna Give You Up", "", 5)
        assert len(results) == 1

    def test_passes_album_and_limit(self, service):
        with patch("app.services.metadata_service.search_itunes") as mock_search:
            mock_search.return_value = []
            service.search_metadata("Artist", "Title", album="Album", limit=3)
        mock_search.assert_called_once_with("Artist", "Title", "Album", 3)

    def test_returns_empty_list_on_no_results(self, service):
        with patch("app.services.metadata_service.search_itunes", return_value=[]):
            results = service.search_metadata("Unknown", "Unknown")
        assert results == []

    def test_reraises_exceptions(self, service):
        with patch("app.services.metadata_service.search_itunes", side_effect=RuntimeError("API down")):
            with pytest.raises(RuntimeError):
                service.search_metadata("Artist", "Title")


class TestFormatMetadataResponse:
    def test_returns_expected_structure(self, service):
        search_params = {"artist": "Rick Astley", "title": "Never"}
        response = service.format_metadata_response([SAMPLE_ITUNES_RESULT], search_params)
        assert response["success"] is True
        assert response["count"] == 1
        assert response["searchParams"] == search_params
        assert len(response["results"]) == 1

    def test_maps_result_fields_correctly(self, service):
        response = service.format_metadata_response([SAMPLE_ITUNES_RESULT], {})
        item = response["results"][0]
        assert item["title"] == "Never Gonna Give You Up"
        assert item["artist"] == "Rick Astley"
        assert item["album"] == "Whenever You Need Somebody"
        assert item["releaseYear"] == 1987
        assert item["explicit"] is False  # trackExplicitness == "notExplicit"
        assert item["isStreamable"] is True
        assert item["rawData"] == SAMPLE_ITUNES_RESULT

    def test_explicit_flag_true_for_explicit_tracks(self, service):
        explicit_result = {**SAMPLE_ITUNES_RESULT, "trackExplicitness": "explicit"}
        response = service.format_metadata_response([explicit_result], {})
        assert response["results"][0]["explicit"] is True

    def test_empty_results(self, service):
        response = service.format_metadata_response([], {})
        assert response["count"] == 0
        assert response["results"] == []
        assert response["success"] is True

    def test_handles_missing_optional_fields(self, service):
        minimal_result = {"title": "Minimal", "artist": "Artist"}
        response = service.format_metadata_response([minimal_result], {})
        item = response["results"][0]
        assert item["album"] == ""
        assert item["metadataId"] == ""
        assert item["releaseYear"] is None
