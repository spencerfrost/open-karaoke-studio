"""Unit tests for metadata filtering utilities."""
import json

from app.utils.metadata import (
    filter_itunes_metadata_for_storage,
    filter_youtube_metadata_for_storage,
)


class TestFilterYoutubeMetadataForStorage:
    def test_returns_json_string(self):
        result = filter_youtube_metadata_for_storage({"title": "Song"})
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["title"] == "Song"

    def test_removes_formats_key(self):
        data = {"title": "Song", "formats": [{"format_id": "22"} for _ in range(50)]}
        result = json.loads(filter_youtube_metadata_for_storage(data))
        assert "formats" not in result
        assert result["title"] == "Song"

    def test_preserves_other_fields(self):
        data = {
            "title": "Rick Roll",
            "uploader": "Rick Astley",
            "duration": 213,
            "description": "The classic",
        }
        result = json.loads(filter_youtube_metadata_for_storage(data))
        assert result["uploader"] == "Rick Astley"
        assert result["duration"] == 213

    def test_handles_non_serializable_values(self):
        class NonSerializable:
            def __str__(self):
                return "custom_object"

        data = {"title": "Song", "custom": NonSerializable()}
        result = json.loads(filter_youtube_metadata_for_storage(data))
        assert result["custom"] == "custom_object"

    def test_handles_nested_non_serializable(self):
        class Obj:
            def __str__(self):
                return "nested_obj"

        data = {"metadata": {"nested": Obj()}}
        result = json.loads(filter_youtube_metadata_for_storage(data))
        assert result["metadata"]["nested"] == "nested_obj"

    def test_handles_empty_dict(self):
        result = json.loads(filter_youtube_metadata_for_storage({}))
        assert result == {}

    def test_handles_non_serializable_in_list(self):
        """Exercises _make_serializable list branch (line 30) via TypeError fallback."""

        class Obj:
            def __str__(self):
                return "obj_repr"

        data = {"items": [Obj(), "text", 42]}
        result = json.loads(filter_youtube_metadata_for_storage(data))
        assert result["items"] == ["obj_repr", "text", 42]

    def test_preserves_list_fields(self):
        data = {"thumbnails": [{"url": "http://a.com"}, {"url": "http://b.com"}]}
        result = json.loads(filter_youtube_metadata_for_storage(data))
        assert len(result["thumbnails"]) == 2


class TestFilterItunesMetadataForStorage:
    def test_extracts_first_result_from_wrapper(self):
        data = {
            "resultCount": 1,
            "results": [{"trackName": "Song", "artistName": "Artist"}],
        }
        result = json.loads(filter_itunes_metadata_for_storage(data))
        assert result["trackName"] == "Song"

    def test_empty_results_returns_empty_dict(self):
        data = {"resultCount": 0, "results": []}
        result = json.loads(filter_itunes_metadata_for_storage(data))
        assert result == {}

    def test_returns_raw_data_when_no_wrapper(self):
        data = {"trackName": "Song", "artistName": "Artist"}
        result = json.loads(filter_itunes_metadata_for_storage(data))
        assert result["trackName"] == "Song"

    def test_handles_empty_dict(self):
        result = json.loads(filter_itunes_metadata_for_storage({}))
        assert result == {}
