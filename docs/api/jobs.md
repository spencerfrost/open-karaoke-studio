# Jobs API

Complete API documentation for background job management and monitoring.

## Base URL

```
/api/jobs
```

## Overview

The Jobs API manages background processing tasks for audio separation, YouTube downloads, and other long-running operations. Jobs are processed asynchronously using Celery workers and updates are broadcast via WebSocket.

## Job Status Values

| Status        | Description                                  |
|--------------|----------------------------------------------|
| `pending`    | Job queued, waiting to start                 |
| `downloading`| Downloading audio from YouTube               |
| `processing` | Audio separation in progress                 |
| `finalizing` | Completing processing, saving files          |
| `completed`  | Job finished successfully                    |
| `failed`     | Job encountered an error                     |
| `cancelled`  | Job was cancelled (not fully implemented)    |

## Endpoints

### Get Job Status Overview

Get aggregate statistics about all jobs in the system.

```http
GET /api/jobs/status
```

#### Response

```json
{
  "total": 45,
  "pending": 2,
  "processing": 1,
  "completed": 40,
  "failed": 2,
  "cancelled": 0
}
```

---

### List All Jobs

Get a list of all jobs with optional filtering.

```http
GET /api/jobs
```

#### Query Parameters

| Parameter          | Type    | Default | Description                              |
|-------------------|---------|---------|------------------------------------------|
| `status`          | string  | None    | Filter by status (see status values above) |
| `include_dismissed` | boolean | false   | Include jobs marked as dismissed         |

#### Response

```json
{
  "jobs": [
    {
      "id": "job-uuid",
      "song_id": "song-uuid",
      "task_id": "celery-task-id",
      "filename": "song_file_identifier",
      "title": "Song Title",
      "artist": "Artist Name",
      "status": "processing",
      "progress": 65,
      "status_message": "Separating vocals...",
      "engine_type": "demucs",
      "created_at": "2026-01-28T10:00:00",
      "started_at": "2026-01-28T10:00:05",
      "completed_at": null,
      "error": null,
      "dismissed": false
    }
  ]
}
```

---

### Get Dismissed Jobs

Get a list of jobs that have been dismissed from the UI.

```http
GET /api/jobs/dismissed
```

#### Response

```json
{
  "jobs": [
    {
      "id": "job-uuid",
      "status": "completed",
      "dismissed": true,
      "completed_at": "2026-01-28T09:30:00"
    }
  ]
}
```

---

### Get Job Details

Get detailed information about a specific job.

```http
GET /api/jobs/{job_id}
```

#### Path Parameters

| Parameter | Type   | Description |
|-----------|--------|-------------|
| `job_id`  | string | Job UUID    |

#### Response

```json
{
  "id": "job-uuid",
  "song_id": "song-uuid",
  "task_id": "celery-task-id",
  "filename": "song_file_identifier",
  "title": "Song Title",
  "artist": "Artist Name",
  "status": "processing",
  "progress": 65,
  "status_message": "Separating vocals with Demucs...",
  "engine_type": "demucs",
  "created_at": "2026-01-28T10:00:00Z",
  "started_at": "2026-01-28T10:00:05Z",
  "completed_at": null,
  "error": null,
  "notes": null,
  "dismissed": false
}
```

#### Error Responses

- `404 Not Found` - Job doesn't exist

```json
{
  "detail": "Job not found"
}
```

---

### Cancel Job

Attempt to cancel a running or pending job.

```http
POST /api/jobs/{job_id}/cancel
```

#### Path Parameters

| Parameter | Type   | Description |
|-----------|--------|-------------|
| `job_id`  | string | Job UUID    |

#### Response

```json
{
  "success": true,
  "message": "Job cancellation requested",
  "job_id": "job-uuid"
}
```

**Note:** Full Celery cancellation is not fully implemented. The job will be marked as cancelled in the database, but the Celery task may continue running. See [Tech Debt](../TECH-DEBT.md#1-celery-job-cancellation-not-implemented) for details.

---

### Dismiss Job

Mark a job as dismissed in the UI (hides it from the jobs queue drawer).

```http
POST /api/jobs/{job_id}/dismiss
```

#### Path Parameters

| Parameter | Type   | Description |
|-----------|--------|-------------|
| `job_id`  | string | Job UUID    |

#### Response

```json
{
  "success": true,
  "message": "Job dismissed successfully",
  "job_id": "job-uuid"
}
```

**Note:** This only affects UI display. The job record remains in the database and can be retrieved with `include_dismissed=true`.

---

### Start Audio Processing

Create a new audio processing job for a song.

```http
POST /api/jobs/process-audio
```

#### Request Body

```json
{
  "song_id": "song-uuid",
  "job_type": "audio_processing"
}
```

#### Response

```json
{
  "id": "job-uuid",
  "song_id": "song-uuid",
  "task_id": "celery-task-id",
  "status": "pending",
  "progress": 0,
  "created_at": "2026-01-28T10:00:00Z"
}
```

---

## Job Progress Phases

Audio processing jobs go through distinct phases with specific progress ranges:

| Phase              | Progress Range | Description                           |
|-------------------|----------------|---------------------------------------|
| **Download**      | 0-30%          | Downloading audio from YouTube        |
| **Separation**    | 30-90%         | AI vocal/instrumental separation      |
| **Finalization**  | 90-100%        | Saving files, updating metadata       |

### Status Messages by Phase

**Download Phase:**
- "Downloading audio from YouTube..."
- "Download complete"

**Separation Phase:**
- "Separating vocals with Demucs..."
- "Separating vocals with Roformer..."
- "Running hybrid separation..."
- "Processing audio (XX%)"

**Finalization Phase:**
- "Finalizing audio files..."
- "Detecting BPM..."
- "Saving metadata..."
- "Processing complete"

**Error States:**
- "Download failed: {error}"
- "Separation failed: {error}"
- "Processing error: {error}"

---

## WebSocket Integration

Jobs broadcast real-time updates via the `/ws/jobs` WebSocket endpoint.

### WebSocket Events

**Subscribe to Job Updates:**
```json
{
  "type": "subscribe_to_jobs"
}
```

**Request Current Jobs List:**
```json
{
  "type": "request_jobs_list"
}
```

**Server Broadcasts:**

**Job Updated:**
```json
{
  "type": "job_updated",
  "job_id": "job-uuid",
  "status": "processing",
  "progress": 45,
  "status_message": "Separating vocals..."
}
```

**Job Completed:**
```json
{
  "type": "job_completed",
  "job_id": "job-uuid",
  "song_id": "song-uuid",
  "status": "completed",
  "progress": 100
}
```

**Job Failed:**
```json
{
  "type": "job_failed",
  "job_id": "job-uuid",
  "status": "failed",
  "error": "Error message"
}
```

---

## Separation Engines

When creating jobs, different audio separation engines can be used:

| Engine          | Speed    | Quality | Use Case                           |
|----------------|----------|---------|-------------------------------------|
| `demucs`       | Fast     | Good    | Default, balanced quality/speed     |
| `roformer`     | Medium   | Better  | Better vocal isolation              |
| `hybrid`       | Slow     | Best    | Multi-stage, highest quality        |
| `clean_backing`| Slowest  | Best    | Experimental, 3-stage processing    |

**Performance (approximate):**
- **GPU:** 2-5 minutes per song
- **CPU:** 10-20 minutes per song

---

## Error Codes

| Error Code                | HTTP Status | Description                    |
|--------------------------|-------------|--------------------------------|
| `RESOURCE_NOT_FOUND`     | 404         | Job doesn't exist              |
| `DATABASE_ERROR`         | 500         | Database operation failed      |
| `SERVICE_ERROR`          | 500         | Job service error              |
| `AUDIO_PROCESSING_ERROR` | 500         | Audio separation failed        |
| `NETWORK_ERROR`          | 502         | YouTube download failed        |

---

## Usage Examples

### Monitor Job Progress

```bash
# Get all active jobs
curl "http://localhost:5123/api/jobs?status=processing"

# Get specific job details
curl http://localhost:5123/api/jobs/job-uuid

# Get job statistics
curl http://localhost:5123/api/jobs/status
```

### Manage Jobs

```bash
# Cancel a job
curl -X POST http://localhost:5123/api/jobs/job-uuid/cancel

# Dismiss a completed job
curl -X POST http://localhost:5123/api/jobs/job-uuid/dismiss

# View dismissed jobs
curl http://localhost:5123/api/jobs/dismissed
```

### Start Processing

```bash
# Start audio processing for a song
curl -X POST http://localhost:5123/api/jobs/process-audio \
  -H "Content-Type: application/json" \
  -d '{
    "song_id": "song-uuid",
    "job_type": "audio_processing"
  }'
```

### WebSocket Connection (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:5123/ws/jobs');

ws.onopen = () => {
  // Subscribe to job updates
  ws.send(JSON.stringify({
    type: 'subscribe_to_jobs'
  }));
  
  // Request current jobs
  ws.send(JSON.stringify({
    type: 'request_jobs_list'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'job_updated':
      console.log(`Job ${data.job_id}: ${data.progress}%`);
      break;
    case 'job_completed':
      console.log(`Job ${data.job_id} completed!`);
      break;
    case 'job_failed':
      console.error(`Job ${data.job_id} failed: ${data.error}`);
      break;
  }
};
```

---

## Related Documentation

- [Songs API](songs.md) - Song management endpoints
- [Architecture: Processing Pipeline](../ARCHITECTURE.md#processing-pipeline) - Audio processing details
- [Tech Debt: Job Cancellation](../TECH-DEBT.md#1-celery-job-cancellation-not-implemented) - Known limitations
- [Error Handling Guide](error-handling.md) - Error codes and handling
