# API Examples - Python

Complete Python examples for integrating with the Open Karaoke Studio API using modern Python patterns with requests, asyncio, and type hints.

## 🎵 Songs API

### Song Service Class

```python
import requests
import asyncio
import aiohttp
from typing import List, Dict, Optional, Any
from pathlib import Path
import json

class SongService:
    def __init__(self, base_url: str = "http://localhost:5123/api"):
        self.base_url = base_url
        self.session = requests.Session()

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with error handling."""
        url = f"{self.base_url}{path}"

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_data = response.json() if response.content else {}
            raise Exception(f"API Error: {error_data.get('error', str(e))}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")

    def get_songs(self) -> List[Dict[str, Any]]:
        """Get all songs in the library."""
        return self._request("GET", "/songs")

    def get_song(self, song_id: str) -> Dict[str, Any]:
        """Get details for a specific song."""
        return self._request("GET", f"/songs/{song_id}")

    def search_songs(self, query: str) -> List[Dict[str, Any]]:
        """Search songs by title, artist, or content."""
        params = {"q": query}
        return self._request("GET", "/songs/search", params=params)

    def create_song(self, song_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new song record."""
        return self._request("POST", "/songs", json=song_data)

    def update_song(self, song_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update song metadata."""
        return self._request("PATCH", f"/songs/{song_id}", json=updates)

    def delete_song(self, song_id: str) -> bool:
        """Delete a song and all its files."""
        try:
            self._request("DELETE", f"/songs/{song_id}")
            return True
        except Exception:
            return False

    def toggle_favorite(self, song_id: str, is_favorite: bool) -> Dict[str, Any]:
        """Toggle favorite status for a song."""
        return self.update_song(song_id, {"favorite": is_favorite})

# Usage examples
song_service = SongService()

# Get all songs
songs = song_service.get_songs()
print(f"Found {len(songs)} songs")

# Search for songs
results = song_service.search_songs("bohemian rhapsody")
print(f"Search results: {len(results)} songs")

# Create a new song
new_song = song_service.create_song({
    "title": "Bohemian Rhapsody",
    "artist": "Queen",
    "album": "A Night at the Opera",
    "year": "1975",
    "source": "youtube",
    "sourceUrl": "https://www.youtube.com/watch?v=fJ9rUzIMcZQ",
    "videoId": "fJ9rUzIMcZQ"
})

# Update song metadata
updated_song = song_service.update_song(new_song["id"], {
    "genre": "Rock",
    "language": "English",
    "favorite": True
})
```

## 📥 File Downloads

### Download Service

```python
import requests
from pathlib import Path
from typing import Union

class DownloadService:
    def __init__(self, base_url: str = "http://localhost:5123/api"):
        self.base_url = base_url
        self.session = requests.Session()

    def download_track(self, song_id: str, track_type: str,
                      output_path: Union[str, Path]) -> bool:
        """Download a specific track type (vocals, instrumental, original)."""
        url = f"{self.base_url}/songs/{song_id}/download/{track_type}"

        try:
            response = self.session.get(url, stream=True)
            response.raise_for_status()

            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"Downloaded {track_type} track to {output_path}")
            return True

        except Exception as e:
            print(f"Download failed: {e}")
            return False

    def get_thumbnail(self, song_id: str, output_path: Union[str, Path],
                     format: str = "auto") -> bool:
        """Download song thumbnail."""
        if format == "auto":
            endpoint = f"/songs/{song_id}/thumbnail"
        else:
            endpoint = f"/songs/{song_id}/thumbnail.{format}"

        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.get(url)
            response.raise_for_status()

            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'wb') as f:
                f.write(response.content)

            print(f"Downloaded thumbnail to {output_path}")
            return True

        except Exception as e:
            print(f"Thumbnail download failed: {e}")
            return False

# Usage examples
download_service = DownloadService()

# Download different track types
download_service.download_track("song-id", "instrumental", "downloads/instrumental.mp3")
download_service.download_track("song-id", "vocals", "downloads/vocals.mp3")
download_service.download_track("song-id", "original", "downloads/original.mp3")

# Download thumbnail
download_service.get_thumbnail("song-id", "downloads/thumbnail.jpg")
```

## 🎤 Lyrics Integration

### Lyrics Service

```python
from typing import Optional, Dict, List

class LyricsService:
    def __init__(self, base_url: str = "http://localhost:5123/api"):
        self.base_url = base_url
        self.session = requests.Session()

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with error handling."""
        url = f"{self.base_url}{path}"
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()

    def search_lyrics(self, artist: str, title: str) -> List[Dict[str, Any]]:
        """Search for lyrics using LRCLIB."""
        params = {"artist": artist, "title": title}
        return self._request("GET", "/lyrics/search", params=params)

    def get_song_lyrics(self, song_id: str) -> Optional[Dict[str, Any]]:
        """Get saved lyrics for a song."""
        try:
            return self._request("GET", f"/lyrics/{song_id}")
        except Exception:
            return None

    def save_lyrics(self, song_id: str, lyrics: str,
                   synced_lyrics: Optional[str] = None) -> Dict[str, Any]:
        """Save lyrics to a song."""
        data = {"lyrics": lyrics}
        if synced_lyrics:
            data["synced_lyrics"] = synced_lyrics
        return self._request("POST", f"/lyrics/{song_id}", json=data)

# Usage examples
lyrics_service = LyricsService()

# Search for lyrics
lyrics_results = lyrics_service.search_lyrics("Queen", "Bohemian Rhapsody")
if lyrics_results:
    lyrics_data = lyrics_results[0]
    print(f"Found lyrics: {lyrics_data.get('plainLyrics', '')[:100]}...")

    # Save to song
    lyrics_service.save_lyrics("song-id", lyrics_data['plainLyrics'],
                              lyrics_data.get('syncedLyrics'))

# Get saved lyrics
saved_lyrics = lyrics_service.get_song_lyrics("song-id")
if saved_lyrics:
    print(f"Saved lyrics: {saved_lyrics['lyrics'][:100]}...")
```

## 🔍 Metadata & Search

### Metadata Service

```python
class MetadataService:
    def __init__(self, base_url: str = "http://localhost:5123/api"):
        self.base_url = base_url
        self.session = requests.Session()

    def search_metadata(self, artist: str, title: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for song metadata using iTunes."""
        params = {"artist": artist, "title": title, "limit": limit}
        response = self.session.get(f"{self.base_url}/metadata/search", params=params)
        response.raise_for_status()
        return response.json()

    def get_artists(self, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """Get artists with pagination."""
        params = {"page": page, "limit": limit}
        response = self.session.get(f"{self.base_url}/songs/artists", params=params)
        response.raise_for_status()
        return response.json()

    def get_songs_by_artist(self, artist_name: str) -> List[Dict[str, Any]]:
        """Get all songs by a specific artist."""
        encoded_name = requests.utils.quote(artist_name)
        response = self.session.get(f"{self.base_url}/songs/by-artist/{encoded_name}")
        response.raise_for_status()
        return response.json()

# Usage examples
metadata_service = MetadataService()

# Search iTunes metadata
metadata_results = metadata_service.search_metadata("Queen", "Bohemian Rhapsody")
print(f"Found {len(metadata_results)} metadata results")

# Get artists with pagination
artists_page = metadata_service.get_artists(page=1, limit=20)
print(f"Artists page 1: {len(artists_page['data'])} of {artists_page['pagination']['total']}")

# Get songs by artist
queen_songs = metadata_service.get_songs_by_artist("Queen")
print(f"Queen has {len(queen_songs)} songs in library")
```

## 🎬 YouTube Integration

### YouTube Service

```python
class YouTubeService:
    def __init__(self, base_url: str = "http://localhost:5123/api"):
        self.base_url = base_url
        self.session = requests.Session()

    def search_youtube(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search for videos on YouTube."""
        params = {"q": query, "max_results": max_results}
        response = self.session.get(f"{self.base_url}/youtube/search", params=params)
        response.raise_for_status()
        return response.json()

    def download_from_youtube(self, url: str, title: str, artist: str) -> Dict[str, Any]:
        """Download and process a YouTube video."""
        data = {"url": url, "title": title, "artist": artist}
        response = self.session.post(f"{self.base_url}/youtube/download", json=data)
        response.raise_for_status()
        return response.json()

# Usage examples
youtube_service = YouTubeService()

# Search YouTube
videos = youtube_service.search_youtube("Queen Bohemian Rhapsody")
print(f"Found {len(videos)} YouTube videos")

# Download a video
if videos:
    video = videos[0]
    download_result = youtube_service.download_from_youtube(
        video['url'],
        "Bohemian Rhapsody",
        "Queen"
    )
    print(f"Download initiated: {download_result}")
```

## 🔄 Jobs & Processing

### Jobs Service with Polling

```python
import time
from typing import Callable, Optional

class JobsService:
    def __init__(self, base_url: str = "http://localhost:5123/api"):
        self.base_url = base_url
        self.session = requests.Session()

    def get_job_status(self) -> Dict[str, Any]:
        """Get overall job processing status."""
        response = self.session.get(f"{self.base_url}/jobs/status")
        response.raise_for_status()
        return response.json()

    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """Get all background jobs."""
        response = self.session.get(f"{self.base_url}/jobs")
        response.raise_for_status()
        return response.json()

    def get_job(self, job_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific job."""
        response = self.session.get(f"{self.base_url}/jobs/{job_id}")
        response.raise_for_status()
        return response.json()

    def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel a running or pending job."""
        response = self.session.post(f"{self.base_url}/jobs/{job_id}/cancel")
        response.raise_for_status()
        return response.json()

    def dismiss_job(self, job_id: str) -> Dict[str, Any]:
        """Remove a completed job from the UI."""
        response = self.session.post(f"{self.base_url}/jobs/{job_id}/dismiss")
        response.raise_for_status()
        return response.json()

    def wait_for_job_completion(self, job_id: str,
                               callback: Optional[Callable] = None,
                               poll_interval: int = 2,
                               timeout: int = 300) -> Dict[str, Any]:
        """Poll job status until completion or timeout."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                job = self.get_job(job_id)

                if callback:
                    callback(job)

                if job['status'] in ['completed', 'failed', 'cancelled']:
                    return job

                time.sleep(poll_interval)

            except Exception as e:
                print(f"Error polling job {job_id}: {e}")
                time.sleep(poll_interval)

        raise TimeoutError(f"Job {job_id} did not complete within {timeout} seconds")

# Usage examples
jobs_service = JobsService()

# Monitor job status
status = jobs_service.get_job_status()
print(f"Job status: {status}")

# Get all jobs
all_jobs = jobs_service.get_all_jobs()
print(f"Active jobs: {len(all_jobs)}")

# Wait for job completion with progress callback
def progress_callback(job):
    print(f"Job {job['id']}: {job['status']} - {job.get('progress', 0)}%")

try:
    completed_job = jobs_service.wait_for_job_completion(
        "job-id-123",
        callback=progress_callback,
        timeout=600
    )
    print(f"Job completed: {completed_job}")
except TimeoutError as e:
    print(f"Job timed out: {e}")
```

## 🎵 Karaoke Queue

### Queue Service

```python
class KaraokeQueueService:
    def __init__(self, base_url: str = "http://localhost:5123"):
        self.base_url = base_url
        self.session = requests.Session()

    def get_queue(self) -> List[Dict[str, Any]]:
        """Get the current karaoke queue."""
        response = self.session.get(f"{self.base_url}/karaoke-queue/")
        response.raise_for_status()
        return response.json()

    def add_to_queue(self, singer_name: str, song_id: str) -> Dict[str, Any]:
        """Add a song to the karaoke queue."""
        data = {"singer_name": singer_name, "song_id": song_id}
        response = self.session.post(f"{self.base_url}/karaoke-queue/", json=data)
        response.raise_for_status()
        return response.json()

    def remove_from_queue(self, item_id: int) -> Dict[str, Any]:
        """Remove an item from the queue."""
        response = self.session.delete(f"{self.base_url}/karaoke-queue/{item_id}")
        response.raise_for_status()
        return response.json()

    def reorder_queue(self, queue_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Reorder the entire queue."""
        data = {"queue": queue_items}
        response = self.session.put(f"{self.base_url}/karaoke-queue/reorder", json=data)
        response.raise_for_status()
        return response.json()

# Usage examples
queue_service = KaraokeQueueService()

# Get current queue
queue = queue_service.get_queue()
print(f"Current queue has {len(queue)} items")

# Add to queue
queue_service.add_to_queue("John Doe", "song-id-123")

# Reorder queue
reordered_queue = [
    {"id": 1, "position": 1},
    {"id": 2, "position": 2},
    {"id": 3, "position": 3}
]
queue_service.reorder_queue(reordered_queue)
```

## 🚀 Async/Await Examples

### Async API Client

```python
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional

class AsyncApiClient:
    def __init__(self, base_url: str = "http://localhost:5123/api"):
        self.base_url = base_url
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """Make async HTTP request."""
        url = f"{self.base_url}{path}"

        async with self.session.request(method, url, **kwargs) as response:
            if not response.ok:
                error_data = await response.json() if response.content else {}
                raise Exception(f"API Error: {error_data.get('error', response.status)}")
            return await response.json()

    async def get_songs(self) -> List[Dict[str, Any]]:
        """Get all songs asynchronously."""
        return await self._request("GET", "/songs")

    async def search_songs(self, query: str) -> List[Dict[str, Any]]:
        """Search songs asynchronously."""
        params = {"q": query}
        return await self._request("GET", "/songs/search", params=params)

    async def get_multiple_songs(self, song_ids: List[str]) -> List[Dict[str, Any]]:
        """Get multiple songs concurrently."""
        tasks = [self._request("GET", f"/songs/{song_id}") for song_id in song_ids]
        return await asyncio.gather(*tasks, return_exceptions=True)

# Async usage examples
async def main():
    async with AsyncApiClient() as client:
        # Get all songs
        songs = await client.get_songs()
        print(f"Found {len(songs)} songs")

        # Search multiple queries concurrently
        search_tasks = [
            client.search_songs("queen"),
            client.search_songs("beatles"),
            client.search_songs("elvis")
        ]
        search_results = await asyncio.gather(*search_tasks)

        for i, results in enumerate(search_results):
            print(f"Search {i+1}: {len(results)} results")

        # Get multiple songs concurrently
        song_ids = [song['id'] for song in songs[:5]]
        detailed_songs = await client.get_multiple_songs(song_ids)
        print(f"Got details for {len(detailed_songs)} songs")

# Run async example
# asyncio.run(main())
```

## 🛠️ Complete Application Example

### Karaoke Library Manager

```python
#!/usr/bin/env python3
"""
Complete Karaoke Library Manager using Open Karaoke Studio API
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

class KaraokeManager:
    def __init__(self, base_url: str = "http://localhost:5123"):
        self.song_service = SongService(f"{base_url}/api")
        self.download_service = DownloadService(f"{base_url}/api")
        self.lyrics_service = LyricsService(f"{base_url}/api")
        self.metadata_service = MetadataService(f"{base_url}/api")
        self.youtube_service = YouTubeService(f"{base_url}/api")
        self.jobs_service = JobsService(f"{base_url}/api")
        self.queue_service = KaraokeQueueService(base_url)

    def list_songs(self, artist_filter: str = None) -> List[Dict[str, Any]]:
        """List all songs, optionally filtered by artist."""
        songs = self.song_service.get_songs()

        if artist_filter:
            songs = [s for s in songs if artist_filter.lower() in s['artist'].lower()]

        return songs

    def search_and_add_from_youtube(self, query: str, artist: str = None) -> bool:
        """Search YouTube and add the first result."""
        try:
            # Search YouTube
            videos = self.youtube_service.search_youtube(query, max_results=1)
            if not videos:
                print(f"No YouTube results found for: {query}")
                return False

            video = videos[0]
            title = video.get('title', query)
            video_artist = artist or video.get('uploader', 'Unknown Artist')

            # Download and process
            result = self.youtube_service.download_from_youtube(
                video['url'], title, video_artist
            )

            print(f"Added '{title}' by {video_artist} to processing queue")
            return True

        except Exception as e:
            print(f"Failed to add from YouTube: {e}")
            return False

    def download_song_files(self, song_id: str, output_dir: str = "downloads"):
        """Download all files for a song."""
        output_path = Path(output_dir) / song_id
        output_path.mkdir(parents=True, exist_ok=True)

        # Download all track types
        tracks = ["instrumental", "vocals", "original"]
        for track_type in tracks:
            try:
                file_path = output_path / f"{track_type}.mp3"
                success = self.download_service.download_track(song_id, track_type, file_path)
                if success:
                    print(f"Downloaded {track_type} track")
            except Exception as e:
                print(f"Failed to download {track_type}: {e}")

        # Download thumbnail
        try:
            thumbnail_path = output_path / "thumbnail.jpg"
            self.download_service.get_thumbnail(song_id, thumbnail_path)
            print("Downloaded thumbnail")
        except Exception as e:
            print(f"Failed to download thumbnail: {e}")

    def add_to_queue_interactive(self):
        """Interactive queue management."""
        songs = self.list_songs()

        if not songs:
            print("No songs in library")
            return

        print("\n=== Song Library ===")
        for i, song in enumerate(songs[:20]):  # Show first 20
            print(f"{i+1:2d}. {song['title']} - {song['artist']}")

        if len(songs) > 20:
            print(f"... and {len(songs) - 20} more songs")

        try:
            choice = int(input("\nSelect song number (0 to exit): "))
            if choice == 0 or choice > len(songs):
                return

            song = songs[choice - 1]
            singer_name = input("Singer name: ").strip()

            if singer_name:
                self.queue_service.add_to_queue(singer_name, song['id'])
                print(f"Added '{song['title']}' to queue for {singer_name}")

        except (ValueError, IndexError, KeyboardInterrupt):
            print("Selection cancelled")

    def show_status(self):
        """Show system status."""
        try:
            # Song library stats
            songs = self.song_service.get_songs()
            print(f"Library: {len(songs)} songs")

            # Job status
            job_status = self.jobs_service.get_job_status()
            print(f"Jobs: {job_status}")

            # Queue status
            queue = self.queue_service.get_queue()
            print(f"Queue: {len(queue)} items")

            if queue:
                print("Next up:")
                for i, item in enumerate(queue[:3]):
                    print(f"  {i+1}. {item['singer_name']}")

        except Exception as e:
            print(f"Error getting status: {e}")

def main():
    parser = argparse.ArgumentParser(description="Karaoke Library Manager")
    parser.add_argument("--url", default="http://localhost:5123",
                       help="API base URL")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # List command
    list_parser = subparsers.add_parser("list", help="List songs")
    list_parser.add_argument("--artist", help="Filter by artist")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add song from YouTube")
    add_parser.add_argument("query", help="Search query")
    add_parser.add_argument("--artist", help="Artist name")

    # Download command
    download_parser = subparsers.add_parser("download", help="Download song files")
    download_parser.add_argument("song_id", help="Song ID")
    download_parser.add_argument("--output", default="downloads", help="Output directory")

    # Queue command
    subparsers.add_parser("queue", help="Interactive queue management")

    # Status command
    subparsers.add_parser("status", help="Show system status")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    manager = KaraokeManager(args.url)

    try:
        if args.command == "list":
            songs = manager.list_songs(args.artist)
            for song in songs:
                print(f"{song['title']} - {song['artist']} ({song['id']})")

        elif args.command == "add":
            success = manager.search_and_add_from_youtube(args.query, args.artist)
            if not success:
                sys.exit(1)

        elif args.command == "download":
            manager.download_song_files(args.song_id, args.output)

        elif args.command == "queue":
            manager.add_to_queue_interactive()

        elif args.command == "status":
            manager.show_status()

    except KeyboardInterrupt:
        print("\nOperation cancelled")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## 📝 Usage Examples

### Run the Karaoke Manager

```bash
# List all songs
python karaoke_manager.py list

# List songs by artist
python karaoke_manager.py list --artist queen

# Add song from YouTube
python karaoke_manager.py add "queen bohemian rhapsody"

# Download all files for a song
python karaoke_manager.py download 123e4567-e89b-12d3-a456-426614174000

# Interactive queue management
python karaoke_manager.py queue

# Show system status
python karaoke_manager.py status
```

This Python API integration guide provides comprehensive examples with error handling, async support, and a complete command-line application for managing the Open Karaoke Studio system.
