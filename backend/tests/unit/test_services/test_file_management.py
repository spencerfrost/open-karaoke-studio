"""
Tests for file_management.py module

Tests for download_image function with WebP support.
"""

from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest
import requests

from app.services.file_management import download_image


class TestDownloadImage:
    """Test download_image function"""

    @patch("app.services.file_management.requests.Session")
    def test_download_image_webp_support(self, mock_session_class):
        """Test that download_image accepts WebP format"""
        # Arrange
        mock_session = Mock()
        mock_session_class.return_value.__enter__.return_value = mock_session

        # Mock WebP response with proper status_code handling
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "image/webp"}
        mock_response.raise_for_status.return_value = None  # No exception

        # WebP signature: RIFF....WEBP
        webp_content = b"RIFF\x00\x00\x75\x5cWEBP" + b"\x00" * 100
        mock_response.iter_content.return_value = [webp_content]

        # Mock both head and get to return proper status
        mock_head_response = Mock()
        mock_head_response.status_code = 200
        mock_session.head.return_value = mock_head_response
        mock_session.get.return_value = mock_response

        url = "https://i.ytimg.com/vi_webp/dQw4w9WgXcQ/maxresdefault.webp"
        save_path = Path("/tmp/test_thumbnail.webp")

        # Act & Assert
        with patch("builtins.open", mock_open()) as mock_file:
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.stat") as mock_stat:
                    mock_stat.return_value.st_size = 1024
                    with patch("pathlib.Path.mkdir"):

                        result = download_image(url, save_path)

                        assert result is True
                        mock_file.assert_called_once_with(save_path, "wb")

    @patch("app.services.file_management.requests.Session")
    def test_download_image_jpeg_support(self, mock_session_class):
        """Test that download_image still accepts JPEG format"""
        # Arrange
        mock_session = Mock()
        mock_session_class.return_value.__enter__.return_value = mock_session

        # Mock JPEG response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "image/jpeg"}

        # JPEG signature
        jpeg_content = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        mock_response.iter_content.return_value = [jpeg_content]

        mock_session.head.return_value = mock_response
        mock_session.get.return_value = mock_response

        url = "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg"
        save_path = Path("/tmp/test_thumbnail.jpg")

        # Act & Assert
        with patch("builtins.open", mock_open()) as mock_file:
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.stat") as mock_stat:
                    mock_stat.return_value.st_size = 1024

                    result = download_image(url, save_path)

                    assert result is True
                    mock_file.assert_called_once_with(save_path, "wb")

    @patch("app.services.file_management.requests.Session")
    def test_download_image_png_support(self, mock_session_class):
        """Test that download_image accepts PNG format"""
        # Arrange
        mock_session = Mock()
        mock_session_class.return_value.__enter__.return_value = mock_session

        # Mock PNG response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "image/png"}

        # PNG signature
        png_content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        mock_response.iter_content.return_value = [png_content]

        mock_session.head.return_value = mock_response
        mock_session.get.return_value = mock_response

        url = "https://example.com/thumbnail.png"
        save_path = Path("/tmp/test_thumbnail.png")

        # Act & Assert
        with patch("builtins.open", mock_open()) as mock_file:
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.stat") as mock_stat:
                    mock_stat.return_value.st_size = 1024

                    result = download_image(url, save_path)

                    assert result is True
                    mock_file.assert_called_once_with(save_path, "wb")

    @patch("app.services.file_management.requests.Session")
    def test_download_image_rejects_invalid_format(self, mock_session_class):
        """Test that download_image rejects non-image content"""
        # Arrange
        mock_session = Mock()
        mock_session_class.return_value.__enter__.return_value = mock_session

        # Mock invalid response (not an image)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html"}

        # Invalid content (not image signature)
        invalid_content = b"<html><body>Not an image</body></html>"
        mock_response.iter_content.return_value = [invalid_content]

        mock_session.head.return_value = mock_response
        mock_session.get.return_value = mock_response

        url = "https://example.com/not-an-image.html"
        save_path = Path("/tmp/test_thumbnail.jpg")

        # Act
        result = download_image(url, save_path)

        # Assert - Should reject invalid content
        assert result is False

    def test_webp_signature_detection(self):
        """Test WebP signature detection logic"""
        # Test valid WebP signatures
        webp_signatures = [
            b"RIFF\x00\x00\x00\x00WEBP",
            b"RIFF\x12\x34\x56\x78WEBP",
            b"RIFFAAAAWEBP\x00\x00\x00\x00",
        ]

        for signature in webp_signatures:
            assert signature.startswith(b"RIFF")
            assert b"WEBP" in signature[:12]

        # Test non-WebP content
        non_webp = [
            b"\xff\xd8\xff\xe0",  # JPEG
            b"\x89PNG\r\n\x1a\n",  # PNG
            b"RIFF\x00\x00\x00\x00AVI ",  # AVI (not WebP)
            b"Some random content",
        ]

        for content in non_webp:
            is_webp = content.startswith(b"RIFF") and b"WEBP" in content[:12]
            if content.startswith(b"RIFF") and b"AVI " in content[:12]:
                assert not is_webp  # AVI should not be detected as WebP
            elif not content.startswith(b"RIFF"):
                assert not is_webp  # Non-RIFF content is not WebP

    @patch("app.services.file_management.requests.Session")
    def test_download_image_content_type_fallback(self, mock_session_class):
        """Test fallback to signature detection when content-type is wrong"""
        # Arrange - YouTube sometimes reports wrong content-type
        mock_session = Mock()
        mock_session_class.return_value.__enter__.return_value = mock_session

        # Mock response with wrong content-type but valid WebP content
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            "content-type": "application/octet-stream"
        }  # Wrong type

        # Valid WebP content
        webp_content = b"RIFF\x00\x00\x75\x5cWEBP" + b"\x00" * 100
        mock_response.iter_content.return_value = [webp_content]

        mock_session.head.return_value = mock_response
        mock_session.get.return_value = mock_response

        url = "https://i.ytimg.com/vi_webp/dQw4w9WgXcQ/maxresdefault.webp"
        save_path = Path("/tmp/test_thumbnail.webp")

        # Act & Assert - Should succeed despite wrong content-type
        with patch("builtins.open", mock_open()) as mock_file:
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.stat") as mock_stat:
                    mock_stat.return_value.st_size = 1024

                    result = download_image(url, save_path)

                    assert result is True
