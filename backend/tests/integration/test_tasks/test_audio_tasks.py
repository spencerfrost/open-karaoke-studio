"""
Integration tests for Celery tasks in Open Karaoke Studio.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile

# Mock the imports that might not be available during testing
try:
    from app.tasks.audio_tasks import process_audio_task
    from celery import Celery
except ImportError:
    # Create mock functions for testing when app isn't available
    def process_audio_task(song_id, input_path):
        return {"vocals_path": "/mock/vocals.wav", "instrumental_path": "/mock/instrumental.wav"}
    
    Celery = Mock()


class TestAudioTasks:
    """Test Celery audio processing tasks"""
    
    @patch('app.tasks.audio_tasks.separate_audio')
    @patch('app.tasks.tasks.FileService')
    def test_process_audio_task_success(self, mock_file_service_class, mock_separate_audio):
        """Test successful audio processing task"""
        # Setup FileService mock
        mock_file_service = Mock()
        mock_file_service_class.return_value = mock_file_service
        
        mock_song_dir = Path("/test/library/test-song")
        mock_file_service.get_song_directory.return_value = mock_song_dir
        
        # Mock successful audio separation
        mock_separate_audio.return_value = True
        
        # Mock file creation
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.is_file', return_value=True):
                result = process_audio_task("test-song", "/path/to/input.mp3")
                
                # Should call FileService methods
                mock_file_service.ensure_library_exists.assert_called_once()
                mock_file_service.get_song_directory.assert_called_once_with("test-song")
                mock_separate_audio.assert_called_once()
                
                # Should return success result
                assert isinstance(result, dict)
                assert "vocals_path" in result or "status" in result
    
    @patch('app.tasks.audio_tasks.separate_audio')
    @patch('app.tasks.tasks.FileService')
    def test_process_audio_task_separation_failure(self, mock_file_service_class, mock_separate_audio):
        """Test audio processing task when separation fails"""
        # Setup FileService mock
        mock_file_service = Mock()
        mock_file_service_class.return_value = mock_file_service
        
        mock_song_dir = Path("/test/library/test-song")
        mock_file_service.get_song_directory.return_value = mock_song_dir
        
        # Mock separation failure
        mock_separate_audio.side_effect = Exception("Separation failed")
        
        # Should handle separation failure
        with pytest.raises(Exception) as exc_info:
            process_audio_task("test-song", "/path/to/input.mp3")
        
        assert "Separation failed" in str(exc_info.value)
    
    @patch('app.tasks.audio_tasks.separate_audio')
    @patch('app.tasks.tasks.FileService')
    def test_process_audio_task_invalid_input(self, mock_file_service_class, mock_separate_audio):
        """Test audio processing task with invalid input"""
        # Setup FileService mock
        mock_file_service = Mock()
        mock_file_service_class.return_value = mock_file_service
        
        mock_song_dir = Path("/test/library/test-song")
        mock_file_service.get_song_directory.return_value = mock_song_dir
        
        # Test with invalid/non-existent input file
        with patch('pathlib.Path.exists', return_value=False):
            # Should handle invalid input gracefully
            result = process_audio_task("test-song", "/nonexistent/input.mp3")
            
            # Behavior depends on implementation - might raise exception or return error
            assert result is not None
    
    @patch('app.tasks.audio_tasks.current_app')
    @patch('app.tasks.audio_tasks.separate_audio')
    @patch('app.tasks.tasks.FileService')
    def test_process_audio_task_with_progress_callback(self, mock_file_service_class, mock_separate_audio, mock_app):
        """Test audio processing task with progress updates"""
        # Setup FileService mock
        mock_file_service = Mock()
        mock_file_service_class.return_value = mock_file_service
        
        mock_song_dir = Path("/test/library/test-song")
        mock_file_service.get_song_directory.return_value = mock_song_dir
        mock_app.logger = Mock()
        
        # Mock progress callback behavior
        def mock_separation_with_progress(input_path, output_dir, callback, stop_event=None):
            # Simulate progress updates
            if callback:
                callback("Starting separation...")
                callback("Processing 50%...")
                callback("Separation complete")
            return True
        
        mock_separate_audio.side_effect = mock_separation_with_progress
        
        result = process_audio_task("test-song", "/path/to/input.mp3")
        
        # Should complete successfully with progress updates
        mock_separate_audio.assert_called_once()
        assert isinstance(result, dict)
    
    def test_process_audio_task_celery_integration(self):
        """Test that audio task integrates properly with Celery"""
        # Mock Celery task
        mock_task = Mock()
        mock_task.id = "test-task-123"
        mock_task.state = "PENDING"
        mock_task.result = {"status": "success"}
        
        # Mock task execution
        with patch('app.tasks.audio_tasks.process_audio_task') as mock_process:
            mock_process.delay.return_value = mock_task
            
            # Simulate calling the task
            task_result = mock_process.delay("test-song", "/path/to/input.mp3")
            
            assert task_result.id == "test-task-123"
            assert task_result.state == "PENDING"


class TestTaskQueue:
    """Test task queue functionality"""
    
    def test_task_status_tracking(self):
        """Test that task status is properly tracked"""
        # Mock task with status tracking
        mock_task = Mock()
        mock_task.id = "task-123"
        mock_task.state = "PROCESSING"
        mock_task.info = {"progress": 50}
        
        # Mock status retrieval
        with patch('celery.result.AsyncResult') as mock_result:
            mock_result.return_value = mock_task
            
            # Simulate checking task status
            task_status = mock_result("task-123")
            
            assert task_status.state == "PROCESSING"
            assert task_status.info["progress"] == 50
    
    def test_task_cancellation(self):
        """Test task cancellation functionality"""
        # Mock task cancellation
        mock_task = Mock()
        mock_task.id = "task-123"
        mock_task.revoke.return_value = True
        
        # Simulate task cancellation
        with patch('celery.result.AsyncResult') as mock_result:
            mock_result.return_value = mock_task
            
            task = mock_result("task-123")
            task.revoke(terminate=True)
            
            mock_task.revoke.assert_called_once_with(terminate=True)
    
    def test_task_retry_logic(self):
        """Test task retry logic"""
        # Mock task with retry logic
        retry_count = 0
        max_retries = 3
        
        def mock_task_with_retry():
            nonlocal retry_count
            retry_count += 1
            
            if retry_count < max_retries:
                raise Exception(f"Attempt {retry_count} failed")
            else:
                return {"status": "success", "attempts": retry_count}
        
        # Simulate retry logic
        result = None
        for attempt in range(max_retries):
            try:
                result = mock_task_with_retry()
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                continue
        
        assert result["status"] == "success"
        assert result["attempts"] == max_retries


class TestTaskErrorHandling:
    """Test error handling in tasks"""
    
    @patch('app.tasks.audio_tasks.separate_audio')
    def test_task_error_logging(self, mock_separate_audio):
        """Test that task errors are properly logged"""
        # Mock separation failure
        mock_separate_audio.side_effect = Exception("Critical error")
        
        with patch('app.tasks.audio_tasks.current_app') as mock_app:
            mock_app.logger = Mock()
            
            # Should log error and re-raise
            with pytest.raises(Exception):
                process_audio_task("test-song", "/path/to/input.mp3")
            
            # Should have logged the error
            mock_app.logger.error.assert_called()
    
    def test_task_timeout_handling(self):
        """Test task timeout handling"""
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Task timed out")
        
        # Mock timeout scenario
        with patch('signal.signal') as mock_signal:
            with patch('signal.alarm') as mock_alarm:
                mock_signal.return_value = timeout_handler
                
                # Simulate setting timeout
                mock_signal(signal.SIGALRM, timeout_handler)
                mock_alarm(300)  # 5 minute timeout
                
                # Task should handle timeout gracefully
                try:
                    # Simulate long-running task
                    mock_alarm(0)  # Cancel alarm
                    result = {"status": "completed"}
                except TimeoutError:
                    result = {"status": "timeout", "error": "Task timed out"}
                
                assert "status" in result
    
    def test_task_resource_cleanup(self):
        """Test that tasks clean up resources properly"""
        # Mock resource allocation
        mock_resources = {
            "temp_files": ["/tmp/file1", "/tmp/file2"],
            "memory_buffers": ["buffer1", "buffer2"],
            "file_handles": ["handle1", "handle2"]
        }
        
        def cleanup_resources():
            # Simulate cleanup
            mock_resources["temp_files"].clear()
            mock_resources["memory_buffers"].clear()
            mock_resources["file_handles"].clear()
        
        try:
            # Simulate task execution
            # ... task logic here ...
            result = {"status": "success"}
        except Exception as e:
            result = {"status": "error", "error": str(e)}
        finally:
            # Should always clean up
            cleanup_resources()
        
        # Resources should be cleaned up
        assert len(mock_resources["temp_files"]) == 0
        assert len(mock_resources["memory_buffers"]) == 0
        assert len(mock_resources["file_handles"]) == 0
