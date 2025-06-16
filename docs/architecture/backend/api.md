# API Reference

**Last Updated**: June 15, 2025  
**API Version**: 2025.1  
**Base URL**: `http://localhost:5000`  

## Overview

The Open Karaoke Studio API provides a comprehensive REST interface for managing karaoke content, background processing, real-time queue management, and user interactions. All endpoints return JSON responses with consistent formatting.

## Authentication

Currently, most endpoints are **publicly accessible**. The user system exists but authentication is optional:

- **Registration**: `POST /users/register` - Create user account (password optional)
- **Login**: `POST /users/login` - Authenticate user session
- **Session-based**: No JWT tokens currently implemented

## Response Format

### Success Response
```json
{
  "success": true,
  "message": "Operation successful",
  "data": { ... }
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error description",
  "errors": { ... }  // Optional field validation details
}
```

## HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| `200` | OK | Successful operation |
| `201` | Created | Resource created successfully |
| `400` | Bad Request | Invalid request parameters |
| `401` | Unauthorized | Authentication required |
| `403` | Forbidden | Access denied |
| `404` | Not Found | Resource not found |
| `500` | Internal Server Error | Server-side error |

## API Endpoints Summary

| Endpoint Group | Count | Purpose |
|---------------|-------|---------|
| **[Songs API](#songs-api)** | 11 | Core content management |
| **[YouTube API](#youtube-api)** | 2 | Video integration |
| **[Jobs API](#jobs-api)** | 6 | Background processing |
| **[Queue API](#queue-api)** | 4 | Real-time karaoke queue |
| **[Lyrics API](#lyrics-api)** | 3 | Text management |
| **[Artists API](#artists-api)** | 3 | Artist discovery |
| **[Users API](#users-api)** | 3 | Authentication |
| **[Metadata API](#metadata-api)** | 1 | Advanced search |

**Total: 35 endpoints**

---

## Songs API

**Base Path**: `/api/songs`  
**Purpose**: Complete song lifecycle management

### Core Operations

#### List All Songs
```http
GET /api/songs
```
**Response**: Array of song objects with full metadata

#### Get Song Details
```http
GET /api/songs/{song_id}
```
**Response**: Complete song object with rich metadata

#### Search Songs
```http
GET /api/songs/search?query={search_term}
```
**Response**: Filtered song array matching search criteria

#### Create Song
```http
POST /api/songs
Content-Type: application/json

{
  "title": "Song Title",
  "artist": "Artist Name",
  "metadata": { ... }
}
```

#### Update Song
```http
PATCH /api/songs/{song_id}
Content-Type: application/json

{
  "title": "Updated Title",
  "favorite": true
}
```

#### Delete Song
```http
DELETE /api/songs/{song_id}
```
**Effect**: Removes song and all associated files

### Audio Downloads

#### Download Audio Track
```http
GET /api/songs/{song_id}/download/{track_type}
```
**Track Types**: `vocals`, `instrumental`, `original`  
**Response**: Binary audio file (MP3)

### Media Assets

#### Get Thumbnail
```http
GET /api/songs/{song_id}/thumbnail
GET /api/songs/{song_id}/thumbnail.{ext}
GET /api/songs/{song_id}/thumbnail.jpg
```
**Response**: Image file (JPEG/WebP)

#### Get Cover Art
```http
GET /api/songs/{song_id}/cover
GET /api/songs/{song_id}/cover.{ext}
```
**Response**: Image file (various formats)

#### Get Lyrics
```http
GET /api/songs/{song_id}/lyrics
```
**Response**: Lyrics object (plain text and/or LRC format)

---

## YouTube API

**Base Path**: `/api/youtube`  
**Purpose**: YouTube video integration

#### Search Videos
```http
GET /api/youtube/search?query={search_term}&maxResults={count}
```
**Parameters**:
- `query` (required): Search terms
- `maxResults` (optional): Number of results (default: 10)

**Response Example**:
```json
{
  "success": true,
  "message": "Found 10 videos matching 'query'",
  "data": [
    {
      "videoId": "dQw4w9WgXcQ",
      "title": "Video Title",
      "channelName": "Channel Name",
      "duration": "3:35",
      "thumbnail": "https://...",
      "description": "..."
    }
  ]
}
```

#### Download Video
```http
POST /api/youtube/download
Content-Type: application/json

{
  "videoId": "dQw4w9WgXcQ",
  "artist": "Artist Name",
  "title": "Song Title"
}
```
**Response**: Background job ID for tracking progress

---

## Jobs API

**Base Path**: `/api/jobs`  
**Purpose**: Background processing management

#### Get System Status
```http
GET /api/jobs/status
```
**Response**: Queue statistics and health metrics

#### List All Jobs
```http
GET /api/jobs/?status={filter}&include_dismissed={boolean}
```
**Parameters**:
- `status` (optional): Filter by job status
- `include_dismissed` (optional): Include dismissed jobs

#### Get Job Details
```http
GET /api/jobs/{job_id}
```
**Response**: Complete job object with progress and metadata

#### Cancel Job
```http
POST /api/jobs/{job_id}/cancel
```
**Effect**: Stops running job and marks as cancelled

#### Dismiss Job
```http
POST /api/jobs/{job_id}/dismiss
```
**Effect**: Hides completed job from main queue view

#### List Dismissed Jobs
```http
GET /api/jobs/dismissed
```
**Response**: All jobs marked as dismissed

### Job Status Values
- `pending` - Queued for processing
- `downloading` - Fetching from YouTube
- `processing` - Audio separation in progress
- `finalizing` - File cleanup and metadata
- `completed` - Successfully finished
- `failed` - Error occurred
- `cancelled` - User cancelled

---

## Queue API

**Base Path**: `/karaoke-queue`  
**Purpose**: Real-time karaoke session management

#### Get Current Queue
```http
GET /karaoke-queue/
```
**Response**: Ordered array of queue items

#### Add to Queue
```http
POST /karaoke-queue/
Content-Type: application/json

{
  "songId": "song-uuid",
  "singerName": "Singer Name"
}
```

#### Remove from Queue
```http
DELETE /karaoke-queue/{item_id}
```

#### Reorder Queue
```http
PUT /karaoke-queue/reorder
Content-Type: application/json

{
  "items": [
    {"id": 1, "position": 0},
    {"id": 3, "position": 1}
  ]
}
```

---

## Lyrics API

**Base Path**: `/api/lyrics`  
**Purpose**: Lyrics search and management

#### Search Lyrics Database
```http
GET /api/lyrics/search?query={search_term}
```

#### Upload/Update Lyrics
```http
POST /api/lyrics/{song_id}
Content-Type: application/json

{
  "lyrics": "Verse 1...\nChorus...",
  "format": "plain"
}
```

#### Get Song Lyrics
```http
GET /api/lyrics/{song_id}
```
**Response**: Lyrics object with plain text and synchronized versions

---

## Artists API

**Base Path**: `/api/songs`  
**Purpose**: Artist discovery and management

#### List All Artists
```http
GET /api/songs/artists
```
**Response**: Array of artist names with song counts

#### Get Songs by Artist
```http
GET /api/songs/by-artist/{artist_name}
```
**Response**: All songs by specified artist

#### Search Artists/Songs
```http
GET /api/songs/search?query={search_term}
```
**Response**: Combined artist and song search results

---

## Users API

**Base Path**: `/users`  
**Purpose**: User management and authentication

#### Register User
```http
POST /users/register
Content-Type: application/json

{
  "username": "user123",
  "password": "optional",
  "display_name": "Display Name"
}
```

#### Login User
```http
POST /users/login
Content-Type: application/json

{
  "username": "user123",
  "password": "required_if_set"
}
```

#### Update User Profile
```http
PATCH /users/{user_id}
Content-Type: application/json

{
  "display_name": "New Name",
  "password": "new_password"
}
```

---

## Metadata API

**Base Path**: `/api/metadata`  
**Purpose**: Advanced search and filtering

#### Advanced Search
```http
GET /api/metadata/search?{complex_parameters}
```
**Purpose**: Multi-field search across all metadata sources

---

## WebSocket Events

The API integrates with WebSocket endpoints for real-time updates:

### Job Progress Events
- **Channel**: `/jobs`
- **Events**: `job_started`, `job_progress`, `job_completed`, `job_failed`

### Queue Update Events
- **Channel**: `/karaoke-queue`
- **Events**: `queue_updated`, `item_added`, `item_removed`, `queue_reordered`

### Performance Control Events
- **Channel**: `/performance-controls`
- **Events**: Session management for live karaoke

---

## Rate Limiting

### Current Limits
- **No rate limiting** currently implemented
- **External API respect** - YouTube and iTunes APIs use internal throttling
- **Resource-based limits** - Large file uploads may timeout

### Recommendations
- **100 requests/minute** per IP for general API usage
- **10 downloads/hour** for YouTube video processing
- **Authenticated users** may have higher limits

---

## Content Type Support

### Audio Files
- **Input**: MP4, WebM, MP3, WAV (via YouTube)
- **Output**: MP3 (320kbps) for all track types
- **Separation**: Vocals, instrumental, original versions

### Image Files
- **Thumbnails**: JPEG (primary), WebP (modern browsers)
- **Cover Art**: JPEG, PNG, WebP with multiple resolutions
- **Dynamic sizing**: Extension-based format negotiation

### Text Content
- **Lyrics**: Plain text and LRC (synchronized) formats
- **Metadata**: JSON with rich typing and validation
- **Search**: Full-text search across all text fields

---

## Error Handling

### Common Error Scenarios

#### YouTube Integration
```json
{
  "success": false,
  "error": "Video not available or restricted"
}
```

#### File Operations
```json
{
  "success": false,
  "error": "Song not found",
  "details": "No audio files available for song ID"
}
```

#### Background Jobs
```json
{
  "success": false,
  "error": "Job processing failed",
  "details": "Audio separation timeout after 10 minutes"
}
```

### Error Recovery
- **Automatic retries** for network-related failures
- **Graceful degradation** when external services unavailable
- **Detailed error messages** for debugging
- **Progress preservation** for long-running operations

---

## Example Workflows

### Complete Song Addition Workflow
```bash
# 1. Search YouTube
GET /api/youtube/search?query=artist+song+name

# 2. Start download and processing
POST /api/youtube/download
{
  "videoId": "found_video_id",
  "artist": "Artist Name",
  "title": "Song Title"
}

# 3. Monitor progress (WebSocket or polling)
GET /api/jobs/{returned_job_id}

# 4. Song becomes available
GET /api/songs/{song_id}

# 5. Download processed audio
GET /api/songs/{song_id}/download/vocals
GET /api/songs/{song_id}/download/instrumental
```

### Live Karaoke Session
```bash
# 1. Get available songs
GET /api/songs

# 2. Add to queue
POST /karaoke-queue/
{"songId": "uuid", "singerName": "John"}

# 3. Monitor queue changes (WebSocket)
# Real-time updates to all connected clients

# 4. Manage queue order
PUT /karaoke-queue/reorder
{"items": [{"id": 1, "position": 0}]}
```

---

**Detailed Endpoint Documentation**:
- [Songs API](songs.md) - Complete song management
- [Jobs API](jobs.md) - Background processing details
- [Queue API](queue.md) - Real-time karaoke features
- [Users API](users.md) - Authentication system
