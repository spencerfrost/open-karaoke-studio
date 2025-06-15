# Background Jobs Service Architecture

## Overview

The Background Jobs Service provides unified job processing for all long-running operations in the system, including YouTube downloads, audio processing, and other asynchronous tasks. It creates a seamless user experience with real-time progress tracking and comprehensive error handling.

## Current Implementation Status

**File**: `backend/app/services/jobs_service.py`  
**Queue**: Celery with Redis backend  
**Status**: Partially implemented, needs YouTube integration enhancement

## Core Responsibilities

### 1. Unified Job Management
- Create jobs immediately when user initiates operations
- Track job progress across multiple processing phases
- Provide real-time status updates via WebSocket
- Handle job cancellation and cleanup

### 2. YouTube Processing Pipeline
- Integrate YouTube downloads into job system
- Provide progress tracking during download phase
- Handle conversion from video to audio formats
- Manage transition to audio processing

### 3. Audio Processing Coordination
- Coordinate with audio separation services
- Track progress during Demucs processing
- Handle GPU/CPU resource management
- Manage output file organization

### 4. Progress Reporting
- Phase-aware progress calculation (0-100%)
- Real-time WebSocket updates
- Detailed status messages for each phase
- Error reporting and recovery

## Job Processing Architecture

### Unified Processing Pipeline

The service implements a unified pipeline that handles the complete YouTube-to-karaoke workflow:

```
User Action → Immediate Job Creation → Download Phase → Audio Processing → Finalization
     ↓              ↓                     ↓              ↓                ↓
  0% Progress   Job Visible          0-30% Progress   30-90% Progress   90-100%
```

### Phase-Based Progress Tracking

Jobs are divided into distinct phases with specific progress ranges:

```python
class JobPhase:
    DOWNLOAD = "download"        # 0-30%: YouTube download + conversion
    PROCESSING = "processing"    # 30-90%: Audio separation
    FINALIZATION = "finalization"  # 90-100%: File saving + cleanup
```

## Service Interface

```python
class JobsServiceInterface(Protocol):
    def create_youtube_job(self, video_id: str, metadata: Dict[str, Any]) -> str:
        """Create job for YouTube processing pipeline"""
        
    def create_audio_job(self, file_path: str, song_id: str) -> str:
        """Create job for audio-only processing"""
        
    def update_job_progress(self, job_id: str, progress: int, message: str, phase: str = None) -> bool:
        """Update job progress and broadcast to clients"""
        
    def cancel_job(self, job_id: str) -> bool:
        """Cancel running job and cleanup resources"""
        
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get current job status and progress"""
        
    def get_active_jobs(self) -> List[Dict[str, Any]]:
        """Get all currently active jobs"""
```

## Implementation Details

### YouTube Job Processing

The service provides unified YouTube processing that creates jobs immediately upon user request:

```python
@celery.task(bind=True, name='process_youtube_job')
def process_youtube_job(self, job_id, video_id, metadata):
    """
    Unified task for YouTube video processing from start to finish
    """
    try:
        # Phase 1: Download (0-30%)
        self.update_progress(0, "Starting YouTube download...")
        download_path = download_youtube_video(job_id, video_id, metadata)
        self.update_progress(20, "Converting to audio format...")
        audio_path = convert_to_audio(download_path)
        self.update_progress(30, "Download complete, starting audio processing...")
        
        # Phase 2: Audio Processing (30-90%)
        self.update_progress(30, "Initializing audio separation...")
        separate_audio_with_progress(audio_path, job_id, self.update_progress_callback)
        self.update_progress(90, "Audio processing complete, finalizing...")
        
        # Phase 3: Finalization (90-100%)
        self.update_progress(90, "Organizing files...")
        finalize_song_files(job_id)
        self.update_progress(100, "Processing complete!")
        
    except Exception as e:
        self.update_progress(-1, f"Error: {str(e)}")
        raise
```

### Progress Callback System

The service implements a sophisticated progress callback system for real-time updates:

```python
def create_progress_callback(self, job_id, phase_start, phase_end):
    """
    Create phase-specific progress callback that maps sub-progress to overall progress
    """
    def progress_callback(sub_progress, message=""):
        # Map sub-progress (0-100) to phase range
        overall_progress = phase_start + (sub_progress * (phase_end - phase_start) / 100)
        self.update_job_progress(job_id, int(overall_progress), message)
        
        # Broadcast via WebSocket
        self.broadcast_job_update(job_id, overall_progress, message)
        
    return progress_callback
```

### Job State Management

Jobs maintain comprehensive state information throughout their lifecycle:

```python
class JobState:
    def __init__(self, job_id: str, job_type: str):
        self.id = job_id
        self.type = job_type
        self.phase = JobPhase.DOWNLOAD
        self.progress = 0
        self.message = "Initializing..."
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.error = None
        self.cancellation_requested = False
```

## Integration Points

### YouTube Service Integration

The Jobs Service coordinates with the YouTube Service for download operations:

```python
# In youtube_service.py
def download_with_progress(self, video_id, progress_callback):
    """
    Download YouTube video with progress reporting
    """
    def ytdlp_progress_hook(d):
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '0%').replace('%', '')
            progress_callback(float(percent), f"Downloading: {percent}%")
    
    ydl_opts = {
        'progress_hooks': [ytdlp_progress_hook],
        # ... other options
    }
```

### Audio Service Integration

Audio processing is coordinated through the Jobs Service:

```python
# In audio_service.py
def separate_with_progress(self, input_path, output_dir, progress_callback):
    """
    Audio separation with progress callbacks
    """
    def demucs_callback(data):
        # Convert Demucs progress to percentage
        progress = calculate_demucs_progress(data)
        progress_callback(progress, f"Separating audio: {progress:.1f}%")
    
    separator = Separator(callback=demucs_callback)
    # ... separation logic
```

### WebSocket Broadcasting

Real-time updates are broadcast to frontend clients:

```python
def broadcast_job_update(self, job_id, progress, message, phase=None):
    """
    Broadcast job updates to connected WebSocket clients
    """
    update_data = {
        'job_id': job_id,
        'progress': progress,
        'message': message,
        'phase': phase,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # Broadcast to all clients monitoring this job
    socketio.emit('job_update', update_data, room=f'job_{job_id}')
    
    # Broadcast to general job monitoring room
    socketio.emit('jobs_update', update_data, room='jobs')
```

## Error Handling

### Comprehensive Error Recovery

The service implements multi-level error handling:

```python
def handle_job_error(self, job_id, error, phase):
    """
    Handle job errors with appropriate recovery strategies
    """
    logger.error(f"Job {job_id} error in {phase}: {error}")
    
    # Update job status
    self.update_job_progress(job_id, -1, f"Error: {str(error)}")
    
    # Attempt recovery based on phase
    if phase == JobPhase.DOWNLOAD:
        return self._retry_download(job_id)
    elif phase == JobPhase.PROCESSING:
        return self._fallback_cpu_processing(job_id)
    else:
        return self._cleanup_failed_job(job_id)
```

### Resource Cleanup

Failed or cancelled jobs trigger comprehensive cleanup:

```python
def cleanup_job_resources(self, job_id):
    """
    Clean up all resources associated with a job
    """
    # Stop any running processes
    self._terminate_job_processes(job_id)
    
    # Clean up temporary files
    self._cleanup_temp_files(job_id)
    
    # Release GPU resources if applicable
    self._release_gpu_memory(job_id)
    
    # Update job status
    self.update_job_progress(job_id, -1, "Job cancelled")
```

## Performance Considerations

### Resource Management
- GPU memory allocation tracking
- CPU usage monitoring for concurrent jobs
- Disk space management for temporary files
- Network bandwidth throttling for downloads

### Concurrency Control
- Maximum concurrent jobs configuration
- Priority queue for high-priority operations
- Resource-aware job scheduling
- Dynamic worker scaling based on load

## User Experience Features

### Immediate Feedback
- Jobs appear in processing queue instantly
- No delay between user action and progress visibility
- Consistent progress reporting across all job types

### Comprehensive Status
- Clear phase indicators (downloading/processing/finalizing)
- Detailed progress messages
- Error reporting with suggested actions
- Estimated time remaining calculations

## Dependencies

### Required Services
- **YouTube Service**: For video download operations
- **Audio Service**: For audio separation processing
- **File Service**: For file organization and cleanup

### External Dependencies
- **Celery**: Task queue management
- **Redis**: Job state storage and message broker
- **WebSocket**: Real-time client communication

## Future Enhancements

### Advanced Features
- Job priority management
- Batch job processing
- Job scheduling and delayed execution
- Cross-session job persistence

### Performance Improvements
- Distributed processing across multiple workers
- GPU resource pooling
- Intelligent job batching
- Predictive resource allocation

### Monitoring and Analytics
- Job performance metrics
- Resource utilization tracking
- Error pattern analysis
- User behavior insights

## Testing Strategy

### Unit Tests
- Job creation and state management
- Progress calculation algorithms
- Error handling scenarios

### Integration Tests
- End-to-end YouTube processing pipeline
- WebSocket communication
- Resource cleanup verification

### Load Tests
- Concurrent job processing
- Resource exhaustion scenarios
- WebSocket connection limits