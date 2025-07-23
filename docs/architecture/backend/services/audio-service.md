# Audio Service Architecture

## Overview

The Audio Service handles audio separation processing using Demucs, providing vocal and instrumental track extraction with real-time progress reporting, GPU acceleration support, and comprehensive error handling. It serves as the core audio processing engine for the karaoke application.

## Current Implementation Status

**File**: `backend/app/services/audio.py`  
**Engine**: Demucs (Facebook Research)  
**Acceleration**: CUDA GPU with CPU fallback  
**Status**: Fully implemented with progress callbacks

## Core Responsibilities

### 1. Audio Separation Processing
- Separate vocals from instrumental tracks using Demucs
- Support multiple audio formats (MP3, WAV, FLAC)
- Handle format conversion and quality optimization
- Manage temporary file processing

### 2. Hardware Acceleration Management
- Detect and utilize GPU acceleration (CUDA)
- Graceful fallback to CPU processing
- Resource management and memory optimization
- Performance monitoring and optimization

### 3. Progress Reporting System
- Real-time progress callbacks during processing
- Phase-based progress tracking
- User cancellation support
- Detailed status messaging

### 4. Quality and Format Management
- Preserve input audio quality
- Support configurable output formats
- Handle bitrate and quality settings
- Audio validation and integrity checking

## Service Interface

The Audio Service provides the primary separation function with comprehensive options:

```python
def separate_audio(
    input_path: Path, 
    song_dir: Path, 
    status_callback, 
    stop_event=None
) -> bool:
    """
    Separates audio file into vocals and instrumental tracks
    
    Args:
        input_path: Path to input audio file
        song_dir: Directory for output files
        status_callback: Function for progress updates
        stop_event: Threading event for cancellation
        
    Returns:
        bool: True on success, False on failure
        
    Raises:
        StopProcessingError: If processing is cancelled
        Exception: For other processing errors
    """
```

## Implementation Details

### Hardware Detection and Setup

The service implements intelligent hardware detection and configuration:

```python
def setup_processing_device():
    """
    Detect and configure optimal processing device
    """
    import torch
    
    # Check CUDA availability
    use_cuda = torch.cuda.is_available()
    
    if use_cuda:
        try:
            device_name = torch.cuda.get_device_name(0)
            logger.info(f"GPU detected: {device_name}")
            return "cuda", device_name
        except RuntimeError as e:
            logger.warning(f"CUDA initialization error: {e}")
            logger.info("Falling back to CPU processing")
            os.environ["CUDA_VISIBLE_DEVICES"] = ""
            return "cpu", "CPU"
    else:
        logger.info("No GPU detected, using CPU processing")
        return "cpu", "CPU"
```

### Demucs Integration

The service integrates with Demucs for high-quality audio separation:

```python
def initialize_demucs_separator(device, model_name):
    """
    Initialize Demucs separator with optimal configuration
    """
    try:
        separator = Separator(
            model=model_name,
            device=device,
            callback=create_progress_callback()
        )
        
        logger.info(f"Demucs initialized: {model_name} on {device}")
        return separator
        
    except Exception as e:
        logger.error(f"Demucs initialization failed: {e}")
        raise AudioProcessingError(f"Failed to initialize audio processor: {e}")
```

### Progress Callback System

Real-time progress reporting is implemented through sophisticated callbacks:

```python
def create_progress_callback(status_callback, stop_event):
    """
    Create progress callback that handles Demucs progress data
    """
    last_update_time = 0
    
    def progress_callback(data):
        nonlocal last_update_time
        
        # Check for cancellation
        if stop_event and stop_event.is_set():
            raise StopProcessingError("Processing stopped by user")
        
        # Throttle updates to avoid flooding
        current_time = time.time()
        if current_time - last_update_time < 0.5 and data["state"] != "end":
            return
        
        # Calculate progress
        total_segments = data.get("audio_length", 0)
        processed_segments = data.get("segment_offset", 0)
        model_idx = data.get("model_idx_in_bag", 0)
        models_count = data.get("models", 1)
        
        # Calculate overall progress
        current_model_progress = (
            processed_segments / total_segments if total_segments > 0 else 0
        )
        overall_progress = (
            (model_idx + current_model_progress) / models_count
            if models_count > 0 else 0
        )
        
        # Report progress
        if data["state"] == "end":
            progress_percent = overall_progress * 100
            message = (
                f"Separating: Model {model_idx + 1}/{models_count} "
                f"(Overall {progress_percent:.1f}%)"
            )
            status_callback(message)
            
        last_update_time = current_time
    
    return progress_callback
```

### Audio File Processing

The service handles the complete audio processing pipeline:

```python
def process_audio_separation(input_path, output_dir, separator, status_callback):
    """
    Execute audio separation with comprehensive error handling
    """
    try:
        # Load and validate input
        status_callback(f"Loading audio file: {input_path.name}")
        
        # Perform separation
        _, separated = separator.separate_audio_file(str(input_path))
        
        if not separated:
            raise AudioProcessingError("Demucs returned no separated tracks")
        
        # Process vocals
        vocals_tensor = separated.get("vocals")
        if vocals_tensor is not None:
            vocals_path = get_vocals_path_stem(output_dir).with_suffix(
                determine_output_format(input_path)
            )
            save_audio_track(vocals_tensor, vocals_path, separator.samplerate)
            status_callback("Vocals track saved successfully")
        else:
            logger.warning("No vocals track found in separation results")
        
        # Process instrumental (combine non-vocal stems)
        instrumental_tensor = create_instrumental_track(separated)
        if instrumental_tensor is not None:
            instrumental_path = get_instrumental_path_stem(output_dir).with_suffix(
                determine_output_format(input_path)
            )
            save_audio_track(instrumental_tensor, instrumental_path, separator.samplerate)
            status_callback("Instrumental track saved successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"Audio processing failed: {e}")
        raise
```

### Format Detection and Optimization

The service automatically determines optimal output formats:

```python
def determine_output_format(input_path):
    """
    Determine optimal output format based on input
    """
    input_extension = input_path.suffix.lower()
    
    # Preserve format for supported types
    if input_extension in [".wav", ".mp3"]:
        return input_extension
    
    # Default to WAV for high quality
    return ".wav"

def get_audio_save_kwargs(output_format, samplerate):
    """
    Get format-specific save parameters
    """
    if output_format == ".mp3":
        config = get_config()
        return {
            "samplerate": samplerate,
            "bitrate": int(config.DEFAULT_MP3_BITRATE),
            "preset": 2
        }
    elif output_format == ".wav":
        return {
            "samplerate": samplerate,
            "bits_per_sample": 16,
            "as_float": False
        }
    else:
        # Default parameters
        return {"samplerate": samplerate}
```

### Instrumental Track Creation

The service intelligently creates instrumental tracks from separated stems:

```python
def create_instrumental_track(separated_tracks):
    """
    Create instrumental track by combining non-vocal stems
    """
    import torch
    
    # Find all non-vocal stems
    instrumental_stems = [
        stem_name for stem_name in separated_tracks 
        if stem_name != "vocals"
    ]
    
    if not instrumental_stems:
        logger.error("No non-vocal stems found for instrumental creation")
        return None
    
    # Start with first stem
    first_stem_name = instrumental_stems[0]
    instrumental_tensor = torch.zeros_like(separated_tracks[first_stem_name])
    
    # Sum all instrumental stems
    for stem_name in instrumental_stems:
        instrumental_tensor += separated_tracks[stem_name]
    
    logger.info(f"Created instrumental from stems: {instrumental_stems}")
    return instrumental_tensor
```

## Error Handling and Recovery

### Cancellation Support

The service supports user cancellation at any point during processing:

```python
class StopProcessingError(Exception):
    """Exception raised when processing is stopped by user"""
    pass

def check_cancellation(stop_event):
    """
    Check if cancellation has been requested
    """
    if stop_event and stop_event.is_set():
        raise StopProcessingError("Processing stopped by user")
```

### GPU Fallback Mechanism

Automatic fallback from GPU to CPU when resources are exhausted:

```python
def handle_gpu_error(error, input_path, output_dir, status_callback):
    """
    Handle GPU-related errors with CPU fallback
    """
    if "CUDA" in str(error) or "out of memory" in str(error):
        logger.warning(f"GPU error: {error}")
        status_callback("GPU error detected, falling back to CPU...")
        
        # Force CPU mode
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
        
        # Retry with CPU
        return separate_audio_cpu_fallback(input_path, output_dir, status_callback)
    else:
        raise error
```

### Resource Cleanup

Comprehensive cleanup ensures no resource leaks:

```python
def cleanup_processing_resources(separator=None, temp_files=None):
    """
    Clean up processing resources
    """
    if separator:
        try:
            # Clear GPU memory if using CUDA
            if hasattr(separator, 'device') and 'cuda' in str(separator.device):
                import torch
                torch.cuda.empty_cache()
        except Exception as e:
            logger.warning(f"Error during GPU cleanup: {e}")
    
    # Clean up temporary files
    if temp_files:
        for temp_file in temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception as e:
                logger.warning(f"Error cleaning up temp file {temp_file}: {e}")
```

## Integration Points

### Jobs Service Integration

The Audio Service integrates with the Jobs Service for progress tracking:

```python
# In jobs_service.py
def create_audio_progress_callback(job_id, phase_start=30, phase_end=90):
    """
    Create callback that maps audio progress to job progress
    """
    def callback(message):
        # Extract progress percentage from message if available
        progress = extract_progress_from_message(message)
        
        # Map to job phase range (30-90% for audio processing)
        job_progress = phase_start + (progress * (phase_end - phase_start) / 100)
        
        # Update job progress
        update_job_progress(job_id, int(job_progress), message)
        
    return callback
```

### File Service Integration

Audio processing coordinates with File Service for path management:

```python
# Integration with FileService
def get_audio_output_paths(song_id, input_format):
    """
    Get output paths for audio files using FileService
    """
    file_service = FileService()
    
    output_format = determine_output_format_extension(input_format)
    
    vocals_path = file_service.get_vocals_path(song_id, output_format)
    instrumental_path = file_service.get_instrumental_path(song_id, output_format)
    
    return vocals_path, instrumental_path
```

## Performance Optimization

### GPU Memory Management

```python
def optimize_gpu_memory(model_name, available_memory):
    """
    Optimize Demucs model selection based on available GPU memory
    """
    memory_requirements = {
        'htdemucs': 4096,      # 4GB
        'htdemucs_ft': 6144,   # 6GB
        'htdemucs_6s': 8192,   # 8GB
    }
    
    if available_memory < memory_requirements.get(model_name, 4096):
        logger.warning(f"Insufficient GPU memory for {model_name}")
        return 'htdemucs'  # Fallback to smaller model
    
    return model_name
```

### Processing Optimization

```python
def optimize_processing_parameters(input_file_size, device):
    """
    Optimize processing parameters based on file size and device
    """
    params = {}
    
    # Adjust batch size based on device and file size
    if device == "cuda":
        if input_file_size > 100 * 1024 * 1024:  # > 100MB
            params['segment'] = 10  # Smaller segments for large files
        else:
            params['segment'] = 40  # Default segment size
    else:
        params['segment'] = 20  # Smaller segments for CPU
    
    return params
```

## Dependencies

### Required Libraries
- **Demucs**: Facebook's music source separation library
- **PyTorch**: Deep learning framework with CUDA support
- **torchaudio**: Audio processing for PyTorch
- **numpy**: Numerical operations

### Internal Dependencies
- **File Service**: For path management and file operations
- **Configuration Service**: For model settings and quality parameters
- **Jobs Service**: For progress tracking and status updates

## Future Enhancements

### Advanced Features
- **Multiple Model Support**: Allow users to select different Demucs models
- **Custom Model Training**: Support for fine-tuned models
- **Real-time Processing**: Stream processing for live audio
- **Batch Processing**: Efficient processing of multiple files

### Quality Improvements
- **Advanced Post-processing**: Noise reduction and enhancement
- **Quality Metrics**: Automatic quality assessment of separated tracks
- **Format Optimization**: Smart format selection based on content
- **Metadata Preservation**: Maintain audio metadata through processing

### Performance Enhancements
- **Distributed Processing**: Multi-GPU and multi-node support
- **Model Caching**: Persistent model loading across sessions
- **Progressive Processing**: Process audio in chunks for memory efficiency
- **Hardware Optimization**: Automatic tuning for specific hardware configurations

## Testing Strategy

### Unit Tests
- Audio format detection and conversion
- Progress callback functionality
- Error handling scenarios
- Resource cleanup verification

### Integration Tests
- End-to-end separation workflow
- GPU/CPU fallback mechanisms
- File service integration
- Jobs service progress reporting

### Performance Tests
- Memory usage monitoring
- Processing time benchmarks
- GPU utilization optimization
- Concurrent processing limits