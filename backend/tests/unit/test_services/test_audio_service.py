"""
Unit tests for the audio service in Open Karaoke Studio.
"""

import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Mock the imports that might not be available during testing
try:
    from app.services.audio import StopProcessingError, separate_audio
except ImportError:
    # Create mock functions for testing when app isn't available
    def separate_audio(*args, **kwargs):
        return True

    class StopProcessingError(Exception):
        pass


class TestAudioService:
    """Test the audio processing service"""

    @patch("app.services.audio.Separator")
    def test_separate_audio_success_with_cuda(self, mock_separator):
        """Test successful audio separation with CUDA available"""
        with patch.dict("sys.modules", {"torch": Mock()}):
            import torch

            mock_torch = torch
            mock_torch.cuda.is_available.return_value = True
            mock_torch.cuda.get_device_name.return_value = "GeForce RTX 3080"
            mock_separator_instance = Mock()
            mock_separator.return_value = mock_separator_instance
            input_path = Path("/test/input.mp3")
            song_dir = Path("/test/output")
            status_callback = Mock()
            with patch("app.services.audio.save_audio") as mock_save_audio:
                result = separate_audio(input_path, song_dir, status_callback)
                assert result is True
                mock_torch.cuda.is_available.assert_called_once()
                mock_torch.cuda.get_device_name.assert_called_once_with(0)
                status_callback.assert_called()

    @patch("app.services.audio.Separator")
    def test_separate_audio_fallback_to_cpu(self, mock_separator):
        """Test audio separation falls back to CPU when CUDA fails"""
        with patch.dict("sys.modules", {"torch": Mock()}):
            import torch

            mock_torch = torch
            mock_torch.cuda.is_available.return_value = True
            mock_torch.cuda.get_device_name.side_effect = RuntimeError(
                "CUDA init failed"
            )
            mock_separator_instance = Mock()
            mock_separator.return_value = mock_separator_instance
            input_path = Path("/test/input.mp3")
            song_dir = Path("/test/output")
            status_callback = Mock()
            with patch("app.services.audio.save_audio") as mock_save_audio:
                with patch("app.services.audio.os.environ") as mock_environ:
                    result = separate_audio(input_path, song_dir, status_callback)
                    mock_environ.__setitem__.assert_called_with(
                        "CUDA_VISIBLE_DEVICES", ""
                    )
                    status_callback.assert_called()

    @patch("app.services.audio.Separator")
    def test_separate_audio_cpu_only(self, mock_separator):
        """Test audio separation with CPU only"""
        with patch.dict("sys.modules", {"torch": Mock()}):
            import torch

            mock_torch = torch
            mock_torch.cuda.is_available.return_value = False
            mock_separator_instance = Mock()
            mock_separator.return_value = mock_separator_instance
            input_path = Path("/test/input.mp3")
            song_dir = Path("/test/output")
            status_callback = Mock()
            with patch("app.services.audio.save_audio") as mock_save_audio:
                result = separate_audio(input_path, song_dir, status_callback)
                status_callback.assert_called()
                calls = status_callback.call_args_list
                cpu_message_found = any("CPU" in str(call) for call in calls)
                assert cpu_message_found

    def test_separate_audio_stop_processing(self):
        """Test that audio separation can be stopped"""
        input_path = Path("/test/input.mp3")
        song_dir = Path("/test/output")
        status_callback = Mock()

        # Create a stop event that's already set
        stop_event = threading.Event()
        stop_event.set()

        with patch("app.services.audio.torch") as mock_torch:
            mock_torch.cuda.is_available.return_value = False

            with patch("app.services.audio.Separator") as mock_separator:
                mock_separator_instance = Mock()
                mock_separator.return_value = mock_separator_instance

                # Mock the progress callback to check stop event
                def mock_separate_call(*args, **kwargs):
                    progress_callback = kwargs.get("progress_callback")
                    if progress_callback:
                        # Simulate calling the progress callback
                        progress_callback(
                            {
                                "state": "processing",
                                "audio_length": 100,
                                "segment_offset": 50,
                                "model_idx_in_bag": 0,
                                "models": 1,
                            }
                        )
                    return Mock()  # Return mock result

                mock_separator_instance.separate.side_effect = mock_separate_call

                # This should raise StopProcessingError
                with pytest.raises(StopProcessingError):
                    separate_audio(input_path, song_dir, status_callback, stop_event)

    def test_separate_audio_progress_callback(self):
        """Test the progress callback functionality"""
        input_path = Path("/test/input.mp3")
        song_dir = Path("/test/output")
        status_callback = Mock()

        with patch("app.services.audio.torch") as mock_torch:
            mock_torch.cuda.is_available.return_value = False

            with patch("app.services.audio.Separator") as mock_separator:
                mock_separator_instance = Mock()
                mock_separator.return_value = mock_separator_instance

                # Mock the separate method to call progress callback
                def mock_separate_call(*args, **kwargs):
                    progress_callback = kwargs.get("progress_callback")
                    if progress_callback:
                        # Simulate progress updates
                        progress_callback(
                            {
                                "state": "processing",
                                "audio_length": 100,
                                "segment_offset": 25,
                                "model_idx_in_bag": 0,
                                "models": 2,
                            }
                        )
                        progress_callback(
                            {
                                "state": "end",
                                "audio_length": 100,
                                "segment_offset": 100,
                                "model_idx_in_bag": 1,
                                "models": 2,
                            }
                        )
                    return Mock()

                mock_separator_instance.separate.side_effect = mock_separate_call

                with patch("app.services.audio.save_audio"):
                    result = separate_audio(input_path, song_dir, status_callback)

                    # Check that status callback was called with progress updates
                    status_callback.assert_called()
                    calls = status_callback.call_args_list

                    # Should have progress messages
                    progress_messages = [
                        call for call in calls if "Separating:" in str(call)
                    ]
                    assert len(progress_messages) > 0

    def test_separate_audio_exception_handling(self):
        """Test that exceptions are properly handled"""
        input_path = Path("/test/input.mp3")
        song_dir = Path("/test/output")
        status_callback = Mock()

        with patch("app.services.audio.torch") as mock_torch:
            mock_torch.cuda.is_available.side_effect = Exception("Torch error")

            # Should handle exceptions gracefully
            with pytest.raises(Exception):
                separate_audio(input_path, song_dir, status_callback)

    def test_separate_audio_no_status_callback(self):
        """Test audio separation with no status callback"""
        input_path = Path("/test/input.mp3")
        song_dir = Path("/test/output")

        with patch("app.services.audio.torch") as mock_torch:
            mock_torch.cuda.is_available.return_value = False

            with patch("app.services.audio.Separator") as mock_separator:
                mock_separator_instance = Mock()
                mock_separator.return_value = mock_separator_instance

                with patch("app.services.audio.save_audio"):
                    with patch("builtins.print") as mock_print:
                        # Should not raise an error when no callback provided
                        result = separate_audio(input_path, song_dir, None)

                        # Should use print as fallback
                        mock_print.assert_called()


class TestStopProcessingError:
    """Test the custom StopProcessingError exception"""

    def test_stop_processing_error_creation(self):
        """Test creating StopProcessingError"""
        error_message = "Processing stopped by user"
        error = StopProcessingError(error_message)

        assert str(error) == error_message
        assert isinstance(error, Exception)

    def test_stop_processing_error_inheritance(self):
        """Test that StopProcessingError inherits from Exception"""
        error = StopProcessingError("test")
        assert isinstance(error, Exception)
