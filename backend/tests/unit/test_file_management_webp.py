"""
Tests for file_management WebP support

Tests for WebP format detection and image validation functionality.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from app.services.file_management import download_image


class TestWebPFormatSupport:
    """Test WebP format detection and validation"""

    @patch("requests.Session")
    def test_download_image_webp_format_validation(self, mock_session_class):
        """Test that WebP format is properly validated"""
        # Arrange
        mock_session = Mock()
        mock_session_class.return_value.__enter__.return_value = mock_session

        # Mock successful response with WebP content
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "image/webp"}
        mock_response.iter_content.return_value = [
            b"RIFF\x1a\x00\x00\x00WEBP"
        ]  # WebP signature
        mock_session.head.return_value = mock_response
        mock_session.get.return_value = mock_response

        # Mock file operations
        with patch("builtins.open", mock_open()) as mock_file, patch(
            "pathlib.Path.exists", return_value=True
        ), patch("pathlib.Path.stat") as mock_stat, patch("pathlib.Path.mkdir"):

            mock_stat.return_value.st_size = 1024  # Non-zero file size

            # Act
            result = download_image(
                "https://example.com/test.webp", Path("/test/path.webp")
            )

            # Assert
            assert result is True
            mock_file.assert_called_once()

    @patch("requests.Session")
    def test_download_image_webp_signature_detection(self, mock_session_class):
        """Test WebP signature detection in content validation"""
        # Arrange
        mock_session = Mock()
        mock_session_class.return_value.__enter__.return_value = mock_session

        # Mock response with incorrect content-type but valid WebP content
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            "content-type": "application/octet-stream"
        }  # Wrong content-type

        # WebP file signature: RIFF....WEBP
        webp_content = b"RIFF\x1a\x00\x00\x00WEBP" + b"\x00" * 100
        mock_response.iter_content.return_value = [webp_content]
        mock_session.head.return_value = mock_response
        mock_session.get.return_value = mock_response

        # Mock file operations
        with patch("builtins.open", mock_open()) as mock_file, patch(
            "pathlib.Path.exists", return_value=True
        ), patch("pathlib.Path.stat") as mock_stat, patch("pathlib.Path.mkdir"):

            mock_stat.return_value.st_size = 1024

            # Act
            result = download_image(
                "https://example.com/test.webp", Path("/test/path.webp")
            )

            # Assert
            assert result is True

    @patch("requests.Session")
    def test_download_image_jpeg_signature_still_works(self, mock_session_class):
        """Test that JPEG signature detection still works"""
        # Arrange
        mock_session = Mock()
        mock_session_class.return_value.__enter__.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "image/jpeg"}

        # JPEG file signature
        jpeg_content = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        mock_response.iter_content.return_value = [jpeg_content]
        mock_session.head.return_value = mock_response
        mock_session.get.return_value = mock_response

        # Mock file operations
        with patch("builtins.open", mock_open()) as mock_file, patch(
            "pathlib.Path.exists", return_value=True
        ), patch("pathlib.Path.stat") as mock_stat, patch("pathlib.Path.mkdir"):

            mock_stat.return_value.st_size = 1024

            # Act
            result = download_image(
                "https://example.com/test.jpg", Path("/test/path.jpg")
            )

            # Assert
            assert result is True

    @patch("requests.Session")
    def test_download_image_png_signature_still_works(self, mock_session_class):
        """Test that PNG signature detection still works"""
        # Arrange
        mock_session = Mock()
        mock_session_class.return_value.__enter__.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "image/png"}

        # PNG file signature
        png_content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        mock_response.iter_content.return_value = [png_content]
        mock_session.head.return_value = mock_response
        mock_session.get.return_value = mock_response

        # Mock file operations
        with patch("builtins.open", mock_open()) as mock_file, patch(
            "pathlib.Path.exists", return_value=True
        ), patch("pathlib.Path.stat") as mock_stat, patch("pathlib.Path.mkdir"):

            mock_stat.return_value.st_size = 1024

            # Act
            result = download_image(
                "https://example.com/test.png", Path("/test/path.png")
            )

            # Assert
            assert result is True

    @patch("requests.Session")
    def test_download_image_rejects_invalid_format(self, mock_session_class):
        """Test that invalid image formats are rejected"""
        # Arrange
        mock_session = Mock()
        mock_session_class.return_value.__enter__.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html"}

        # Invalid content (not an image)
        invalid_content = b"<!DOCTYPE html><html>..."
        mock_response.iter_content.return_value = [invalid_content]
        mock_session.head.return_value = mock_response
        mock_session.get.return_value = mock_response

        # Act
        result = download_image(
            "https://example.com/not-image.html", Path("/test/path.jpg")
        )

        # Assert
        assert result is False

    @patch("requests.Session")
    def test_download_image_webp_edge_cases(self, mock_session_class):
        """Test WebP edge cases and variations"""
        # Arrange
        mock_session = Mock()
        mock_session_class.return_value.__enter__.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "image/webp"}

        # WebP with different content but valid signature
        webp_content = b"RIFF\x2a\x01\x00\x00WEBPVP8L" + b"\x00" * 200
        mock_response.iter_content.return_value = [webp_content]
        mock_session.head.return_value = mock_response
        mock_session.get.return_value = mock_response

        # Mock file operations
        with patch("builtins.open", mock_open()) as mock_file, patch(
            "pathlib.Path.exists", return_value=True
        ), patch("pathlib.Path.stat") as mock_stat, patch("pathlib.Path.mkdir"):

            mock_stat.return_value.st_size = 2048

            # Act
            result = download_image(
                "https://example.com/test.webp", Path("/test/path.webp")
            )

            # Assert
            assert result is True


class TestFormatDetectionEdgeCases:
    """Test edge cases in format detection"""

    @patch("requests.Session")
    def test_download_image_malformed_webp_rejected(self, mock_session_class):
        """Test that malformed WebP files are rejected"""
        # Arrange
        mock_session = Mock()
        mock_session_class.return_value.__enter__.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "image/webp"}

        # Malformed WebP (has RIFF but no WEBP signature)
        malformed_content = b"RIFF\x1a\x00\x00\x00TEST" + b"\x00" * 100
        mock_response.iter_content.return_value = [malformed_content]
        mock_session.head.return_value = mock_response
        mock_session.get.return_value = mock_response

        # Act
        result = download_image(
            "https://example.com/malformed.webp", Path("/test/path.webp")
        )

        # Assert
        assert result is False

    @patch("requests.Session")
    def test_download_image_short_content_handling(self, mock_session_class):
        """Test handling of very short content that might not have full signatures"""
        # Arrange
        mock_session = Mock()
        mock_session_class.return_value.__enter__.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "image/jpeg"}

        # Very short content (less than 12 bytes for WebP check)
        short_content = b"\xff\xd8\xff"  # Partial JPEG signature
        mock_response.iter_content.return_value = [short_content]
        mock_session.head.return_value = mock_response
        mock_session.get.return_value = mock_response

        # Act
        result = download_image("https://example.com/short.jpg", Path("/test/path.jpg"))

        # Assert - Should still work for JPEG even with short content
        assert result is False  # Fails because content is too short to be valid
