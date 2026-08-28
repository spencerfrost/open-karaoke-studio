"""Unit tests for YouTubeService._cookie_opts — no yt-dlp, no network, no DB."""
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.services.youtube_service import YouTubeService


@pytest.fixture
def service():
    mock_file_service = MagicMock()
    return YouTubeService(file_service=mock_file_service)


class TestCookieOpts:
    def test_returns_empty_when_unset(self, service, monkeypatch):
        monkeypatch.delenv("YTDLP_COOKIES_FILE", raising=False)
        opts, tmp_path = service._cookie_opts()
        assert opts == {}
        assert tmp_path is None

    def test_returns_empty_when_blank(self, service, monkeypatch):
        monkeypatch.setenv("YTDLP_COOKIES_FILE", "")
        opts, tmp_path = service._cookie_opts()
        assert opts == {}
        assert tmp_path is None

    def test_returns_empty_when_file_missing(self, service, monkeypatch, tmp_path):
        missing = tmp_path / "does-not-exist.txt"
        monkeypatch.setenv("YTDLP_COOKIES_FILE", str(missing))
        opts, tmp_copy = service._cookie_opts()
        assert opts == {}
        assert tmp_copy is None

    def test_returns_empty_when_file_unreadable(self, service, monkeypatch, tmp_path):
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text("# Netscape HTTP Cookie File\n")
        cookie_file.chmod(0o000)
        try:
            if os.access(cookie_file, os.R_OK):
                pytest.skip("running as a user that bypasses file permissions")
            monkeypatch.setenv("YTDLP_COOKIES_FILE", str(cookie_file))
            opts, tmp_copy = service._cookie_opts()
            assert opts == {}
            assert tmp_copy is None
        finally:
            cookie_file.chmod(0o644)

    def test_returns_cookiefile_for_readable_file(self, service, monkeypatch, tmp_path):
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text("# Netscape HTTP Cookie File\n")
        monkeypatch.setenv("YTDLP_COOKIES_FILE", str(cookie_file))

        opts, tmp_copy = service._cookie_opts()

        assert tmp_copy is not None
        assert opts == {"cookiefile": tmp_copy}
        assert Path(tmp_copy).exists()
        assert Path(tmp_copy) != cookie_file
        assert Path(tmp_copy).read_text() == cookie_file.read_text()

        Path(tmp_copy).unlink(missing_ok=True)
