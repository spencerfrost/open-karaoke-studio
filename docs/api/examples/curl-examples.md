# API Examples - cURL

Complete cURL examples for all Open Karaoke Studio API endpoints, based on the actual implementation.

## 🎵 Songs API

### Get All Songs

```bash
# Get all processed songs in the library
curl -X GET "http://localhost:5123/api/songs" \
  -H "Accept: application/json"
```

### Get Song Details

```bash
# Get detailed information for a specific song
curl -X GET "http://localhost:5123/api/songs/{song_id}" \
  -H "Accept: application/json"
```

### Search Songs

```bash
# Search songs by title, artist, or content
curl -X GET "http://localhost:5123/api/songs/search?q=bohemian+rhapsody" \
  -H "Accept: application/json"
```

### Create New Song

```bash
# Create a new song record
curl -X POST "http://localhost:5123/api/songs" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Bohemian Rhapsody",
    "artist": "Queen",
    "album": "A Night at the Opera",
    "source": "youtube",
    "video_id": "fJ9rUzIMcZQ"
  }'
```

### Update Song Metadata

```bash
# Update any song fields
curl -X PATCH "http://localhost:5123/api/songs/{song_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Title",
    "artist": "Updated Artist",
    "year": 1975
  }'
```

### Delete Song

```bash
# Delete a song and all its files
curl -X DELETE "http://localhost:5123/api/songs/{song_id}"
```

## 📥 File Downloads

### Download Instrumental Track

```bash
# Download the instrumental (music-only) version
curl -X GET "http://localhost:5123/api/songs/{song_id}/download/instrumental" \
  -o "song_instrumental.mp3"
```

### Download Vocals Track

```bash
# Download the vocals-only version
curl -X GET "http://localhost:5123/api/songs/{song_id}/download/vocals" \
  -o "song_vocals.mp3"
```

### Download Original Track

```bash
# Download the original audio file
curl -X GET "http://localhost:5123/api/songs/{song_id}/download/original" \
  -o "song_original.mp3"
```

## 🖼️ Media Assets

### Get Thumbnail (Auto-detect Format)

```bash
# Get thumbnail, automatically detecting format (webp, jpg, png)
curl -X GET "http://localhost:5123/api/songs/{song_id}/thumbnail" \
  -o "thumbnail.jpg"
```

### Get Album Cover

```bash
# Get the album cover (albumId comes from the song details response)
curl -X GET "http://localhost:5123/api/albums/{album_id}/cover" \
  -o "cover_art.jpg"
```

## 🎤 Lyrics API

### Search Lyrics

```bash
# Search for lyrics using LRCLIB
curl -X GET "http://localhost:5123/api/lyrics/search?artist_name=Queen&track_name=Bohemian+Rhapsody" \
  -H "Accept: application/json"
```

### Get Song Lyrics

```bash
# Get saved lyrics for a song
curl -X GET "http://localhost:5123/api/lyrics/songs/{song_id}" \
  -H "Accept: application/json"
```

### Save Lyrics

```bash
# Save synced lyrics to a song (type is 'plain' or 'synced')
curl -X POST "http://localhost:5123/api/lyrics/songs/{song_id}?type=synced" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "[00:00.00] Is this the real life?\n[00:03.00] Is this just fantasy?"
  }'
```

## 🔍 Metadata & Search

### Search MusicBrainz

```bash
# Search MusicBrainz recordings (requires authentication)
curl -X GET "http://localhost:5123/api/musicbrainz/search?query=Queen+Bohemian+Rhapsody" \
  -H "Authorization: Bearer {token}"
```

### Get Artists List

```bash
# Get all artists in the library with pagination
curl -X GET "http://localhost:5123/api/songs/artists?offset=0&limit=20" \
  -H "Accept: application/json"
```

### Get Songs by Artist

```bash
# Get all songs by a specific artist
curl -X GET "http://localhost:5123/api/songs/by-artist/Queen" \
  -H "Accept: application/json"
```

## 🎬 YouTube Integration

### Search YouTube

```bash
# Search for videos on YouTube
curl -X GET "http://localhost:5123/api/youtube/search?q=Queen+Bohemian+Rhapsody" \
  -H "Accept: application/json"
```

### Download from YouTube

```bash
# Download and process a YouTube video
# Requires a logged-in account or active session membership
curl -X POST "http://localhost:5123/api/youtube/download" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {token}" \
  -d '{
    "video_id": "fJ9rUzIMcZQ",
    "song_id": "123e4567-e89b-12d3-a456-426614174000",
    "title": "Bohemian Rhapsody",
    "artist": "Queen"
  }'
```

## 🔄 Jobs & Processing

### Get Job Status Overview

```bash
# Get overall processing status
curl -X GET "http://localhost:5123/api/jobs/status" \
  -H "Accept: application/json"
```

### List All Jobs

```bash
# Get all background jobs
curl -X GET "http://localhost:5123/api/jobs" \
  -H "Accept: application/json"
```

### Get Specific Job Details

```bash
# Get detailed information about a job
curl -X GET "http://localhost:5123/api/jobs/{job_id}" \
  -H "Accept: application/json"
```

### Cancel Job

```bash
# Cancel a running or pending job
curl -X POST "http://localhost:5123/api/jobs/{job_id}/cancel" \
  -H "Content-Type: application/json"
```

Note: all Jobs API endpoints require host authentication (`Authorization: Bearer {token}`).

## 🎵 Karaoke Queue

### Get Current Queue

```bash
# Get the current karaoke queue
curl -X GET "http://localhost:5123/api/karaoke-queue?session_code=ABCD" \
  -H "Accept: application/json"
```

### Add Song to Queue

```bash
# Add a song to the karaoke queue
curl -X POST "http://localhost:5123/api/karaoke-queue?session_code=ABCD" \
  -H "Content-Type: application/json" \
  -d '{
    "singer": "John Doe",
    "songId": "123e4567-e89b-12d3-a456-426614174000"
  }'
```

### Remove from Queue

```bash
# Remove a song from the queue
curl -X DELETE "http://localhost:5123/api/karaoke-queue/{item_id}?session_code=ABCD"
```

### Reorder Queue

```bash
# Reorder the entire queue
curl -X PUT "http://localhost:5123/api/karaoke-queue/reorder?session_code=ABCD" \
  -H "Content-Type: application/json" \
  -d '{
    "queue": [
      {"id": 1, "position": 1},
      {"id": 2, "position": 2},
      {"id": 3, "position": 3}
    ]
  }'
```

### Load Queue Item as Current

```bash
# Load a queued song as current (does not auto-play)
curl -X POST "http://localhost:5123/api/karaoke-queue/{item_id}/play?session_code=ABCD"
```

## 👥 User Management

### Register User

```bash
# Register a new user (if authentication is enabled)
curl -X POST "http://localhost:5123/api/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "secure_password",
    "display_name": "John Doe"
  }'
```

### Login User

```bash
# Login with credentials
curl -X POST "http://localhost:5123/api/users/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "secure_password"
  }'
```

### Update User Profile

```bash
# Update user preferences
curl -X PATCH "http://localhost:5123/api/users/{user_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "John Smith",
    "password": "new_password"
  }'
```

## 🔧 Advanced Examples

### Complete Song Processing Workflow

```bash
# 1. Create a song record
SONG_ID=$(curl -s -X POST "http://localhost:5123/api/songs" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Song", "artist": "Test Artist"}' | \
  jq -r '.id')

# 2. Check if processing is needed
curl -X GET "http://localhost:5123/api/songs/$SONG_ID" \
  -H "Accept: application/json"

# 3. Monitor job progress
curl -X GET "http://localhost:5123/api/jobs/status" \
  -H "Accept: application/json"

# 4. Download results when complete
curl -X GET "http://localhost:5123/api/songs/$SONG_ID/download/instrumental" \
  -o "instrumental.mp3"
```

### Batch Operations

```bash
# Get all songs and process metadata
curl -s -X GET "http://localhost:5123/api/songs" | \
  jq -r '.[].id' | \
  while read song_id; do
    echo "Processing song: $song_id"
    curl -X GET "http://localhost:5123/api/songs/$song_id"
  done
```

## 📋 Response Format Examples

All API responses follow a consistent JSON format:

### Success Response

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "Bohemian Rhapsody",
  "artist": "Queen",
  "status": "completed",
  "dateAdded": "2025-06-15T10:30:00Z"
}
```

### Error Response

```json
{
  "error": "Song not found",
  "details": "No song with ID 123e4567-e89b-12d3-a456-426614174000 exists"
}
```

### Paginated Response

```json
{
  "songs": [...],
  "pagination": {
    "total": 156,
    "limit": 20,
    "offset": 0,
    "hasMore": true
  }
}
```

## 🚀 Production Considerations

### Rate Limiting

```bash
# Respect rate limits for external APIs
curl -X GET "http://localhost:5123/api/songs/search?q=Queen" \
  -H "Accept: application/json" \
  --max-time 30
```

### Error Handling

```bash
# Always check HTTP status codes
HTTP_STATUS=$(curl -s -o /tmp/response.json -w "%{http_code}" \
  "http://localhost:5123/api/songs/invalid-id")

if [ $HTTP_STATUS -eq 200 ]; then
  echo "Success: $(cat /tmp/response.json)"
else
  echo "Error $HTTP_STATUS: $(cat /tmp/response.json)"
fi
```

