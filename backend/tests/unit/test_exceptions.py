"""Unit tests for app/exceptions.py — all custom exception classes."""
import pytest

from app.exceptions import (
    AudioProcessingError,
    ConfigurationError,
    DatabaseError,
    DuplicateResourceError,
    FileOperationError,
    FileSystemError,
    InvalidTrackTypeError,
    JobError,
    KaraokeBaseError,
    NetworkError,
    NotFoundError,
    RequestValidationError,
    ResourceNotFoundError,
    ServiceError,
    ValidationError,
    YouTubeError,
)


class TestKaraokeBaseError:
    def test_message_stored(self):
        e = KaraokeBaseError("something went wrong")
        assert e.message == "something went wrong"
        assert str(e) == "something went wrong"

    def test_error_code_optional(self):
        e = KaraokeBaseError("msg")
        assert e.error_code is None

    def test_error_code_set(self):
        e = KaraokeBaseError("msg", error_code="ERR_001")
        assert e.error_code == "ERR_001"

    def test_details_defaults_to_empty_dict(self):
        e = KaraokeBaseError("msg")
        assert e.details == {}

    def test_details_set(self):
        e = KaraokeBaseError("msg", details={"key": "value"})
        assert e.details == {"key": "value"}

    def test_is_exception(self):
        with pytest.raises(KaraokeBaseError):
            raise KaraokeBaseError("boom")


class TestSimpleSubclasses:
    """Test that all leaf exception subclasses are properly wired."""

    def test_service_error_is_karaoke_base_error(self):
        e = ServiceError("svc")
        assert isinstance(e, KaraokeBaseError)

    def test_not_found_error(self):
        e = NotFoundError("nope")
        assert isinstance(e, ServiceError)

    def test_validation_error(self):
        e = ValidationError("bad input")
        assert isinstance(e, ServiceError)

    def test_database_error(self):
        e = DatabaseError("db fail")
        assert isinstance(e, ServiceError)

    def test_audio_processing_error(self):
        e = AudioProcessingError("demucs fail")
        assert isinstance(e, ServiceError)

    def test_youtube_error(self):
        e = YouTubeError("yt fail")
        assert isinstance(e, ServiceError)

    def test_file_system_error(self):
        e = FileSystemError("fs fail")
        assert isinstance(e, ServiceError)

    def test_job_error(self):
        e = JobError("job fail")
        assert isinstance(e, ServiceError)

    def test_network_error(self):
        e = NetworkError("net fail")
        assert isinstance(e, ServiceError)

    def test_configuration_error(self):
        e = ConfigurationError("cfg fail")
        assert isinstance(e, KaraokeBaseError)


class TestRequestValidationError:
    def test_basic(self):
        e = RequestValidationError("bad request")
        assert e.message == "bad request"
        assert e.error_code == "REQUEST_VALIDATION_ERROR"

    def test_with_field(self):
        e = RequestValidationError("bad field", field="title")
        assert e.details["field"] == "title"

    def test_with_value(self):
        e = RequestValidationError("bad value", value="xyz")
        assert e.details["value"] == "xyz"

    def test_with_field_and_value(self):
        e = RequestValidationError("err", field="url", value="not-a-url")
        assert e.details["field"] == "url"
        assert e.details["value"] == "not-a-url"

    def test_no_field_no_value(self):
        e = RequestValidationError("plain error")
        assert "field" not in e.details
        assert "value" not in e.details


class TestResourceNotFoundError:
    def test_message_formatted(self):
        e = ResourceNotFoundError("Song", "song-123")
        assert "Song" in e.message
        assert "song-123" in e.message

    def test_error_code(self):
        e = ResourceNotFoundError("Job", "j-1")
        assert e.error_code == "RESOURCE_NOT_FOUND"

    def test_details(self):
        e = ResourceNotFoundError("Song", "s-1")
        assert e.details["resource_type"] == "Song"
        assert e.details["resource_id"] == "s-1"


class TestDuplicateResourceError:
    def test_message_formatted(self):
        e = DuplicateResourceError("Song", "my-id")
        assert "Song" in e.message
        assert "my-id" in e.message

    def test_error_code(self):
        e = DuplicateResourceError("User", "u-1")
        assert e.error_code == "DUPLICATE_RESOURCE"

    def test_details(self):
        e = DuplicateResourceError("Song", "s-id")
        assert e.details["resource_type"] == "Song"
        assert e.details["identifier"] == "s-id"


class TestFileOperationError:
    def test_basic_message(self):
        e = FileOperationError("read", "/tmp/file.mp3")
        assert "read" in e.message
        assert "/tmp/file.mp3" in e.message

    def test_with_reason(self):
        e = FileOperationError("delete", "/tmp/x.mp3", reason="permission denied")
        assert "permission denied" in e.message
        assert e.details["reason"] == "permission denied"

    def test_without_reason(self):
        e = FileOperationError("write", "/tmp/y.mp3")
        assert "reason" not in e.details

    def test_error_code(self):
        e = FileOperationError("copy", "/tmp/z.mp3")
        assert e.error_code == "FILE_OPERATION_ERROR"

    def test_details_contain_operation_and_path(self):
        e = FileOperationError("move", "/path/to/file")
        assert e.details["operation"] == "move"
        assert e.details["file_path"] == "/path/to/file"


class TestInvalidTrackTypeError:
    def test_message_contains_type(self):
        e = InvalidTrackTypeError("drums")
        assert "drums" in e.message

    def test_default_valid_types(self):
        e = InvalidTrackTypeError("drums")
        assert "vocals" in e.message
        assert "instrumental" in e.message
        assert "original" in e.message

    def test_custom_valid_types(self):
        e = InvalidTrackTypeError("bad", valid_types=["a", "b"])
        assert e.details["valid_types"] == ["a", "b"]

    def test_error_code(self):
        e = InvalidTrackTypeError("bad")
        assert e.error_code == "INVALID_TRACK_TYPE"

    def test_details(self):
        e = InvalidTrackTypeError("drum")
        assert e.details["requested_type"] == "drum"
