import pytest

from app.services.lyrics_language import normalize_language, supports_word_alignment


@pytest.mark.parametrize(
    ("value", "expected"),
    [("fr", "fr"), (" FR ", "fr"), ("haw", "haw"), ("", None), (None, None)],
)
def test_normalize_language_accepts_whisper_codes_and_blank(value, expected):
    assert normalize_language(value) == expected


@pytest.mark.parametrize("value", ["french", "xx", "fr-CA"])
def test_normalize_language_rejects_codes_whisper_does_not_know(value):
    with pytest.raises(ValueError):
        normalize_language(value)


@pytest.mark.parametrize(
    ("language", "supported"),
    [("en", True), ("fr", True), ("ja", False), ("zh", False), ("sw", False)],
)
def test_supports_word_alignment(language, supported):
    assert supports_word_alignment(language) is supported
