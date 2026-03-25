# AI-Generated Lyrics Implementation Guide

## Overview

This document outlines the investigation and implementation strategy for adding AI-generated lyrics functionality to Open Karaoke Studio using Speech-to-Text (STT) models. The feature will leverage isolated vocal tracks produced by Demucs to generate accurate lyric transcriptions.

## Background

Open Karaoke Studio currently separates vocals from music using Demucs, creating isolated vocal tracks that are ideal for speech-to-text processing. By adding STT capabilities, we can automatically generate lyrics from these clean vocal tracks, eliminating the need for manual lyric entry or external lyric databases.

## Technical Requirements

### Hardware Requirements
- **CPU Processing**: Basic functionality with longer processing times
- **GPU Processing**: Recommended for production use (CUDA-compatible)
- **Memory**: 4GB+ RAM for small models, 8GB+ for larger models
- **Storage**: 1-10GB for model files depending on model size

### Software Dependencies
- Python 3.8+
- PyTorch (already included in project)
- Audio processing libraries (already available via Demucs dependencies)

## STT Model Options Analysis

### 1. OpenAI Whisper (Original)
**Pros:**
- State-of-the-art accuracy
- Multilingual support (99 languages)
- Open source (MIT license)
- Robust handling of accents and noise
- Word-level timestamps available

**Cons:**
- Slow inference on CPU
- Large model sizes (39MB - 1.5GB)
- Memory intensive

**Use Case:** High accuracy requirements, multilingual content

### 2. Faster Whisper (Recommended)
**Pros:**
- 4x faster than original Whisper
- Same accuracy as original
- Optimized for both CPU and GPU
- Lower memory usage
- Compatible API with original Whisper
- Active community support

**Cons:**
- Additional dependency (ctranslate2)
- Slightly more complex setup

**Use Case:** Production deployment, best balance of speed and accuracy

### 3. Whisper.cpp
**Pros:**
- Extremely fast CPU inference
- Minimal dependencies
- Cross-platform compatibility
- Very low memory usage

**Cons:**
- C++ integration complexity
- Limited Python bindings
- Fewer features than Python implementations

**Use Case:** Resource-constrained environments

### 4. Alternative Models
- **Vosk**: Offline, lightweight, but lower accuracy
- **DeepSpeech**: Mozilla's solution, discontinued
- **Wav2Vec2**: Facebook's model, good for research

## Recommended Implementation: Faster Whisper

Based on the analysis, **Faster Whisper** provides the optimal balance of accuracy, speed, and ease of integration for Open Karaoke Studio.

### Model Size Options
- **tiny**: 39MB, fastest, basic accuracy
- **base**: 74MB, good balance for most use cases
- **small**: 244MB, better accuracy
- **medium**: 769MB, high accuracy
- **large-v2**: 1.5GB, highest accuracy

**Recommendation**: Start with `base` model for development, allow users to configure model size based on their hardware capabilities.

## Integration Architecture

### Backend Changes

#### 1. New Dependencies
Add to `requirements.txt`:
```
faster-whisper>=0.10.0
```

#### 2. New API Endpoint
```
POST /api/songs/{song_id}/generate-lyrics
```

#### 3. Processing Pipeline Integration
```
Audio Upload → Demucs Separation → Vocals Available → STT Processing → Lyrics Generated
```

#### 4. Database Schema Extension
Add lyrics-related fields to song metadata:
- `lyrics_text`: Generated lyrics content
- `lyrics_timestamps`: Word/segment timing data
- `lyrics_confidence`: STT confidence scores
- `lyrics_generated_at`: Timestamp of generation
- `lyrics_model_used`: STT model version used

### Frontend Changes

#### 1. UI Components
- Lyrics generation button/toggle
- Lyrics display panel
- Edit lyrics functionality
- Confidence indicators

#### 2. API Integration
- New fetch calls for lyrics generation
- Real-time progress updates via WebSocket
- Error handling for STT failures

## Implementation Phases

### Phase 1: Core STT Integration
- [ ] Install and configure Faster Whisper
- [ ] Create basic STT service class
- [ ] Add simple API endpoint for lyrics generation
- [ ] Implement basic error handling

### Phase 2: Async Processing
- [ ] Integrate with existing Celery task queue
- [ ] Add progress tracking
- [ ] Implement retry logic for failed transcriptions

### Phase 3: Advanced Features
- [ ] Word-level timestamps for karaoke sync
- [ ] Multiple model size support
- [ ] Lyrics confidence scoring
- [ ] Manual lyrics editing interface

### Phase 4: Performance Optimization
- [ ] Model caching strategies
- [ ] GPU acceleration configuration
- [ ] Batch processing for multiple songs

## Code Structure

### Backend File Organization
```
backend/app/
├── services/
│   ├── stt_service.py          # STT processing logic
│   └── lyrics_service.py       # Lyrics management
├── models/
│   └── lyrics.py               # Database models
├── routes/
│   └── lyrics_routes.py        # API endpoints
└── jobs/
    └── lyrics_jobs.py         # Celery jobs
```

### Configuration Options
```python
# config.py
STT_MODEL_SIZE = os.getenv('STT_MODEL_SIZE', 'base')
STT_DEVICE = os.getenv('STT_DEVICE', 'auto')  # auto, cpu, cuda
STT_COMPUTE_TYPE = os.getenv('STT_COMPUTE_TYPE', 'int8')
```

## Performance Considerations

### Processing Time Estimates
- **3-minute song on CPU (base model)**: 30-60 seconds
- **3-minute song on GPU (base model)**: 5-15 seconds
- **Larger models**: 2-3x longer processing time

### Memory Usage
- **Base model**: ~1GB RAM during processing
- **Large model**: ~3GB RAM during processing
- **GPU**: Additional VRAM requirements (1-4GB)

### Optimization Strategies
1. **Model Preloading**: Keep model in memory between requests
2. **Audio Preprocessing**: Normalize and optimize audio before STT
3. **Chunking**: Process long audio files in segments
4. **Caching**: Store results to avoid reprocessing

## Error Handling Strategy

### Common Failure Scenarios
1. **Audio Quality Issues**: Too much noise, unclear vocals
2. **Model Loading Failures**: Insufficient memory, missing dependencies
3. **Processing Timeouts**: Very long audio files
4. **Language Detection**: Non-supported languages

### Error Response Format
```json
{
  "error": "stt_processing_failed",
  "message": "Unable to process vocals for transcription",
  "details": {
    "reason": "audio_quality_insufficient",
    "confidence_threshold": 0.3,
    "actual_confidence": 0.15
  }
}
```

## Security Considerations

### Data Privacy
- Audio files are processed locally (no external API calls)
- Generated lyrics stored in local database
- No data transmitted to external services

### Resource Protection
- Rate limiting on STT endpoints
- Memory usage monitoring
- Processing timeout limits

## Testing Strategy

### Unit Tests
- STT service functionality
- Audio preprocessing
- Error handling scenarios

### Integration Tests
- End-to-end lyrics generation
- API endpoint responses
- Database storage/retrieval

### Performance Tests
- Processing time benchmarks
- Memory usage profiling
- Concurrent request handling

## Deployment Considerations

### Docker Integration
Update existing Dockerfiles to include STT dependencies:
```dockerfile
# Add to backend Dockerfile
RUN pip install faster-whisper
```

### Model Distribution
- Models downloaded on first use
- Consider pre-downloading in Docker image for faster startup
- Allow configuration of model download location

### Hardware Scaling
- CPU-only deployment for basic functionality
- GPU deployment for production performance
- Horizontal scaling considerations for multiple workers

## Future Enhancements

### Advanced Features
1. **Speaker Diarization**: Identify multiple singers
2. **Language Detection**: Automatic language identification
3. **Lyrics Timing Sync**: Perfect karaoke timing alignment
4. **Quality Assessment**: Automatic transcription quality scoring
5. **Custom Model Training**: Fine-tuning on karaoke-specific content

### Integration Opportunities
1. **Existing Lyrics Sources**: Compare STT results with LRCLIB data
2. **Music Metadata**: Enhance lyrics with song structure information
3. **Vocal Effects**: Integrate with planned audio effects system

## Conclusion

Implementing AI-generated lyrics using Faster Whisper provides a robust, accurate, and efficient solution for automatic lyric transcription in Open Karaoke Studio. The isolated vocal tracks from Demucs create ideal conditions for high-quality STT processing, making this a natural and valuable addition to the project's feature set.

The phased implementation approach allows for gradual rollout while maintaining system stability, and the modular architecture ensures easy maintenance and future enhancements.

## References

- [Faster Whisper GitHub Repository](https://github.com/guillaumekln/faster-whisper)
- [OpenAI Whisper Documentation](https://github.com/openai/whisper)
- [Demucs Audio Separation](https://github.com/facebookresearch/demucs)
- [Speech Recognition Best Practices](https://huggingface.co/blog/asr-chunking)
