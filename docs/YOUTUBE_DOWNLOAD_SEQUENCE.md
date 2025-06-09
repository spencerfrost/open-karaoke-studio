# YouTube Download Sequence Diagram

## Complete Flow: Frontend → Backend → Celery Worker

This diagram shows the exact sequence of events triggered by the YouTube download mutation in the Open Karaoke Studio project.

```mermaid
sequenceDiagram
    participant User
    participant Frontend as React Frontend<br/>(YouTubeSearch.tsx)
    participant SongAPI as Song API<br/>(/api/songs)
    participant YouTubeAPI as YouTube API<br/>(/api/youtube/download)
    participant YouTubeService as YouTube Service<br/>(youtube_service.py)
    participant Database as SQLite Database
    participant JobStore as Job Storage<br/>(job_store)
    participant Celery as Celery Broker<br/>(Redis/RabbitMQ)
    participant Worker as Celery Worker<br/>(process_youtube_job)

    Note over User,Worker: Phase 1: Song Creation
    User->>Frontend: Click "Download" on YouTube result
    Frontend->>SongAPI: POST /api/songs<br/>{title, artist, album, source: "youtube", videoId}
    SongAPI->>Database: INSERT song record
    Database-->>SongAPI: song_id (UUID)
    SongAPI-->>Frontend: {id: song_id, title, artist, status: "pending"}
    
    Note over Frontend: Store created song data<br/>setCreatedSong(data)

    Note over User,Worker: Phase 2: YouTube Download Job Creation
    Frontend->>YouTubeAPI: POST /api/youtube/download<br/>{videoId, title, artist, album, songId}
    YouTubeAPI->>YouTubeService: download_and_process_async(video_id, artist, title, song_id)
    
    Note over YouTubeService: Validate song_id parameter<br/>Extract video_id from URL/ID

    YouTubeService->>Database: get_song(song_id)
    alt Song exists
        Database-->>YouTubeService: song record
    else Song not found
        YouTubeService->>Database: create_or_update_song(song_id, metadata)
        Database-->>YouTubeService: created song
    end

    Note over YouTubeService: Generate job_id = uuid4()

    YouTubeService->>JobStore: save_job(Job{<br/>  id: job_id,<br/>  song_id: song_id,<br/>  status: PENDING,<br/>  filename: "original.mp3",<br/>  title, artist, notes: {video_id}<br/>})
    JobStore->>Database: INSERT job record
    Database-->>JobStore: success
    JobStore-->>YouTubeService: job saved

    YouTubeService->>JobStore: get_job(job_id) [verification]
    JobStore->>Database: SELECT job WHERE id = job_id
    Database-->>JobStore: job record
    JobStore-->>YouTubeService: verified job exists

    Note over YouTubeService: Queue Celery task

    YouTubeService->>Celery: process_youtube_job.delay(job_id, video_id, metadata)
    Celery-->>YouTubeService: task_id
    
    YouTubeService->>JobStore: update job.task_id = task_id
    JobStore->>Database: UPDATE job SET task_id
    
    YouTubeService-->>YouTubeAPI: job_id
    YouTubeAPI-->>Frontend: {jobId: job_id, status: "pending", message: "YouTube processing job created"}
    Frontend->>User: Show "Download started" toast

    Note over User,Worker: Phase 3: Background Processing
    Worker->>Celery: Pick up process_youtube_job task
    Worker->>JobStore: get_job(job_id)
    JobStore->>Database: SELECT job WHERE id = job_id
    
    alt Job found
        Database-->>JobStore: job record
        JobStore-->>Worker: job with song_id
        
        Worker->>Database: get_song(song_id) [verification]
        alt Song found
            Database-->>Worker: song record
            
            Note over Worker: Update job status to DOWNLOADING
            Worker->>JobStore: save_job(status=DOWNLOADING, progress=5%)
            JobStore->>Database: UPDATE job
            
            Note over Worker: Phase 3a: YouTube Download
            Worker->>Worker: YouTubeService.download_video(video_id, song_id)
            Note over Worker: yt-dlp downloads audio to<br/>karaoke_library/{song_id}/original.mp3
            
            Note over Worker: Update progress to 30%
            Worker->>JobStore: save_job(progress=30%, message="Download complete")
            
            Note over Worker: Phase 3b: Audio Processing
            Worker->>Worker: AudioService.separate_audio(song_id)
            Note over Worker: Demucs separates vocals/instrumentals<br/>Creates vocals.wav, no_vocals.wav
            
            Note over Worker: Update progress to 90%
            Worker->>JobStore: save_job(progress=90%, message="Processing complete")
            
            Note over Worker: Phase 3c: Finalization
            Worker->>Database: update_song_status(song_id, "completed")
            Worker->>JobStore: save_job(status=COMPLETED, progress=100%)
            
            Worker-->>Celery: Task completed successfully
            
        else Song not found
            Database-->>Worker: null
            Worker->>JobStore: save_job(status=FAILED, error="Song not found")
            Worker-->>Celery: Task failed - Song not found
        end
        
    else Job not found
        JobStore-->>Worker: null
        Worker-->>Celery: Task failed - Job not found
    end

    Note over User,Worker: Phase 4: Status Updates (via WebSocket)
    Note over Frontend: User can monitor progress via<br/>real-time updates or polling
```

## Critical Points in the Flow

### 1. **Race Condition Prevention**
- Song is created FIRST via dedicated API endpoint
- YouTube download waits for song creation success
- Service layer verifies song exists before creating job

### 2. **Database Persistence Verification**
- Job is saved to database BEFORE queuing Celery task
- Service layer verifies job persistence with get_job() call
- Worker performs additional existence checks for both job and song

### 3. **Error Handling Points**
- **Frontend**: Song creation failure stops the flow
- **YouTube API**: Missing songId returns 400 error
- **Service Layer**: Song verification, job persistence verification
- **Worker**: Job not found, Song not found (fail fast, no retries)

### 4. **Current Architecture Benefits**
- Clear separation of concerns (song creation vs. processing)
- Robust error handling at each layer
- Database consistency before async processing
- Comprehensive logging for debugging

### 5. **Potential Issues Addressed**
- **Original Issue**: Job creation in API controller caused race conditions
- **Fix**: Moved job creation to service layer with verification
- **Database Transactions**: Ensure job persistence before queuing
- **Worker Validation**: Fail fast if prerequisites are missing

## Key Files in the Flow

1. **Frontend**: `frontend/src/components/upload/YouTubeSearch.tsx`
2. **Song API**: `backend/app/api/songs.py`
3. **YouTube API**: `backend/app/api/youtube.py`
4. **Service Layer**: `backend/app/services/youtube_service.py`
5. **Celery Job**: `backend/app/jobs/jobs.py` (`process_youtube_job`)
6. **Database**: `backend/app/db/database.py`
7. **Job Storage**: `backend/app/db/models/job.py`

## Debugging Tips

When investigating "Job not found" or "Song not found" errors:

1. Check if song was created successfully in Phase 1
2. Verify job was saved to database in Phase 2 (check logs for "Job {job_id} successfully saved")
3. Confirm Celery task was queued (check logs for "queued successfully with task {task_id}")
4. Check worker logs for job/song retrieval attempts
5. Verify database consistency between job creation and worker execution
