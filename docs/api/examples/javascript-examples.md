# API Examples - JavaScript

Complete JavaScript examples for integrating with the Open Karaoke Studio API using modern fetch API and async/await patterns.

## 🎵 Songs API

### SongService Class

```javascript
class SongService {
  constructor(baseUrl = "http://localhost:5123/api") {
    this.baseUrl = baseUrl;
  }

  async request(path, options = {}) {
    const url = `${this.baseUrl}${path}`;
    const config = {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      credentials: "include",
      ...options,
    };

    const response = await fetch(url, config);

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ error: "Network error" }));
      throw new Error(error.error || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Get all songs
  async getAllSongs() {
    return this.request("/songs");
  }

  // Get song details
  async getSong(songId) {
    return this.request(`/songs/${songId}`);
  }

  // Search songs
  async searchSongs(query) {
    const params = new URLSearchParams({ q: query });
    return this.request(`/songs/search?${params}`);
  }

  // Create new song
  async createSong(songData) {
    return this.request("/songs", {
      method: "POST",
      body: JSON.stringify(songData),
    });
  }

  // Update song
  async updateSong(songId, updates) {
    return this.request(`/songs/${songId}`, {
      method: "PATCH",
      body: JSON.stringify(updates),
    });
  }

  // Delete song
  async deleteSong(songId) {
    return this.request(`/songs/${songId}`, {
      method: "DELETE",
    });
  }
}
```

### Basic Usage Examples

```javascript
const songService = new SongService();

// Get all songs
try {
  const songs = await songService.getAllSongs();
  console.log(`Found ${songs.length} songs:`, songs);
} catch (error) {
  console.error("Failed to fetch songs:", error.message);
}

// Search for songs
const searchResults = await songService.searchSongs("bohemian rhapsody");
console.log("Search results:", searchResults);

// Create a new song
const newSong = await songService.createSong({
  title: "Bohemian Rhapsody",
  artist: "Queen",
  album: "A Night at the Opera",
  year: "1975",
  source: "youtube",
  sourceUrl: "https://www.youtube.com/watch?v=fJ9rUzIMcZQ",
  videoId: "fJ9rUzIMcZQ",
});

// Update song metadata
await songService.updateSong(newSong.id, {
  genre: "Rock",
  language: "English",
});
```

## 📥 File Downloads

### Download Service

```javascript
class DownloadService {
  constructor(baseUrl = "http://localhost:5123/api") {
    this.baseUrl = baseUrl;
  }

  async downloadTrack(songId, trackType, filename) {
    const url = `${this.baseUrl}/songs/${songId}/download/${trackType}`;

    try {
      const response = await fetch(url, { credentials: "include" });

      if (!response.ok) {
        throw new Error(`Download failed: ${response.status}`);
      }

      const blob = await response.blob();

      // Create download link
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = filename || `${songId}_${trackType}.mp3`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);

      return true;
    } catch (error) {
      console.error("Download failed:", error);
      throw error;
    }
  }

  async getThumbnail(songId, format = "auto") {
    const endpoint =
      format === "auto"
        ? `/songs/${songId}/thumbnail`
        : `/songs/${songId}/thumbnail.${format}`;

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      credentials: "include",
    });

    if (!response.ok) {
      throw new Error(`Failed to get thumbnail: ${response.status}`);
    }

    return response.blob();
  }
}

// Usage examples
const downloadService = new DownloadService();

// Download instrumental track
await downloadService.downloadTrack(
  "song-id",
  "instrumental",
  "my_song_instrumental.mp3"
);

// Download vocals
await downloadService.downloadTrack("song-id", "vocals", "my_song_vocals.mp3");

// Get thumbnail as blob for display
const thumbnailBlob = await downloadService.getThumbnail("song-id");
const thumbnailUrl = URL.createObjectURL(thumbnailBlob);
document.getElementById("thumbnail").src = thumbnailUrl;
```

## 🎤 Lyrics Integration

### Lyrics Service

```javascript
class LyricsService {
  constructor(baseUrl = "http://localhost:5123/api") {
    this.baseUrl = baseUrl;
  }

  async request(path, options = {}) {
    const response = await fetch(`${this.baseUrl}${path}`, {
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      ...options,
    });

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ error: "Request failed" }));
      throw new Error(error.error || `HTTP ${response.status}`);
    }

    return response.json();
  }

  async searchLyrics(artist, title) {
    const params = new URLSearchParams({ artist, title });
    return this.request(`/lyrics/search?${params}`);
  }

  async getSongLyrics(songId) {
    return this.request(`/lyrics/${songId}`);
  }

  async saveLyrics(songId, lyrics, syncedLyrics = null) {
    return this.request(`/lyrics/${songId}`, {
      method: "POST",
      body: JSON.stringify({
        lyrics,
        synced_lyrics: syncedLyrics,
      }),
    });
  }
}

// Usage examples
const lyricsService = new LyricsService();

// Search for lyrics
const lyricsResults = await lyricsService.searchLyrics(
  "Queen",
  "Bohemian Rhapsody"
);
if (lyricsResults.length > 0) {
  const lyrics = lyricsResults[0];
  console.log("Found lyrics:", lyrics);

  // Save to song
  await lyricsService.saveLyrics(
    "song-id",
    lyrics.plainLyrics,
    lyrics.syncedLyrics
  );
}

// Get saved lyrics
const savedLyrics = await lyricsService.getSongLyrics("song-id");
console.log("Saved lyrics:", savedLyrics);
```

## 🔍 Metadata & Search

### Metadata Service

```javascript
class MetadataService {
  constructor(baseUrl = "http://localhost:5123/api") {
    this.baseUrl = baseUrl;
  }

  async searchMetadata(artist, title, limit = 5) {
    const params = new URLSearchParams({
      artist,
      title,
      limit: limit.toString(),
    });
    const response = await fetch(`${this.baseUrl}/metadata/search?${params}`, {
      credentials: "include",
    });
    return response.json();
  }

  async getArtists(page = 1, limit = 20) {
    const params = new URLSearchParams({
      page: page.toString(),
      limit: limit.toString(),
    });
    const response = await fetch(`${this.baseUrl}/songs/artists?${params}`, {
      credentials: "include",
    });
    return response.json();
  }

  async getSongsByArtist(artistName) {
    const response = await fetch(
      `${this.baseUrl}/songs/by-artist/${encodeURIComponent(artistName)}`,
      {
        credentials: "include",
      }
    );
    return response.json();
  }
}

// Usage examples
const metadataService = new MetadataService();

// Search iTunes metadata
const metadata = await metadataService.searchMetadata(
  "Queen",
  "Bohemian Rhapsody"
);
console.log("iTunes metadata:", metadata);

// Get artists with pagination
const artistsPage = await metadataService.getArtists(1, 20);
console.log(
  `Artists (page 1): ${artistsPage.data.length} of ${artistsPage.pagination.total}`
);

// Get all songs by an artist
const queenSongs = await metadataService.getSongsByArtist("Queen");
console.log("Queen songs:", queenSongs);
```

## 🎬 YouTube Integration

### YouTube Service

```javascript
class YouTubeService {
  constructor(baseUrl = "http://localhost:5123/api") {
    this.baseUrl = baseUrl;
  }

  async searchYouTube(query, maxResults = 10) {
    const params = new URLSearchParams({
      q: query,
      max_results: maxResults.toString(),
    });
    const response = await fetch(`${this.baseUrl}/youtube/search?${params}`, {
      credentials: "include",
    });
    return response.json();
  }

  async downloadFromYouTube(url, title, artist) {
    const response = await fetch(`${this.baseUrl}/youtube/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ url, title, artist }),
    });
    return response.json();
  }
}

// Usage examples
const youtubeService = new YouTubeService();

// Search YouTube
const videos = await youtubeService.searchYouTube("Queen Bohemian Rhapsody");
console.log("YouTube results:", videos);

// Download a video
const downloadResult = await youtubeService.downloadFromYouTube(
  "https://www.youtube.com/watch?v=fJ9rUzIMcZQ",
  "Bohemian Rhapsody",
  "Queen"
);
console.log("Download initiated:", downloadResult);
```

## 🔄 Jobs & Processing

### Jobs Service with Real-time Updates

```javascript
class JobsService {
  constructor(baseUrl = "http://localhost:5123/api") {
    this.baseUrl = baseUrl;
    this.eventListeners = new Map();
  }

  async getJobStatus() {
    const response = await fetch(`${this.baseUrl}/jobs/status`, {
      credentials: "include",
    });
    return response.json();
  }

  async getAllJobs() {
    const response = await fetch(`${this.baseUrl}/jobs`, {
      credentials: "include",
    });
    return response.json();
  }

  async getJob(jobId) {
    const response = await fetch(`${this.baseUrl}/jobs/${jobId}`, {
      credentials: "include",
    });
    return response.json();
  }

  async cancelJob(jobId) {
    const response = await fetch(`${this.baseUrl}/jobs/${jobId}/cancel`, {
      method: "POST",
      credentials: "include",
    });
    return response.json();
  }

  async dismissJob(jobId) {
    const response = await fetch(`${this.baseUrl}/jobs/${jobId}/dismiss`, {
      method: "POST",
      credentials: "include",
    });
    return response.json();
  }

  // WebSocket connection for real-time updates
  connectToJobUpdates(callbacks = {}) {
    const socket = io(`${this.baseUrl.replace("http", "ws")}/jobs`);

    socket.on("connect", () => {
      console.log("Connected to job updates");
      callbacks.onConnect?.();
      socket.emit("subscribe_to_jobs");
    });

    socket.on("job_update", (data) => {
      callbacks.onJobUpdate?.(data);
    });

    socket.on("jobs_list", (data) => {
      callbacks.onJobsList?.(data);
    });

    socket.on("disconnect", () => {
      console.log("Disconnected from job updates");
      callbacks.onDisconnect?.();
    });

    return socket;
  }
}

// Usage examples
const jobsService = new JobsService();

// Monitor job status
const status = await jobsService.getJobStatus();
console.log("Job status:", status);

// Get all jobs
const allJobs = await jobsService.getAllJobs();
console.log("All jobs:", allJobs);

// Real-time job monitoring
const socket = jobsService.connectToJobUpdates({
  onConnect: () => console.log("Connected to real-time updates"),
  onJobUpdate: (job) => console.log("Job updated:", job),
  onJobsList: (jobs) => console.log("Jobs list updated:", jobs),
  onDisconnect: () => console.log("Disconnected from updates"),
});

// Cancel a job
await jobsService.cancelJob("job-id-123");
```

## 🎵 Karaoke Queue

### Queue Service with Real-time Updates

```javascript
class KaraokeQueueService {
  constructor(baseUrl = "http://localhost:5123") {
    this.baseUrl = baseUrl;
  }

  async getQueue() {
    const response = await fetch(`${this.baseUrl}/karaoke-queue/`, {
      credentials: "include",
    });
    return response.json();
  }

  async addToQueue(singerName, songId) {
    const response = await fetch(`${this.baseUrl}/karaoke-queue/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        singer_name: singerName,
        song_id: songId,
      }),
    });
    return response.json();
  }

  async removeFromQueue(itemId) {
    const response = await fetch(`${this.baseUrl}/karaoke-queue/${itemId}`, {
      method: "DELETE",
      credentials: "include",
    });
    return response.json();
  }

  async reorderQueue(queueItems) {
    const response = await fetch(`${this.baseUrl}/karaoke-queue/reorder`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ queue: queueItems }),
    });
    return response.json();
  }

  // WebSocket for real-time queue updates
  connectToQueueUpdates(callbacks = {}) {
    const socket = io(`${this.baseUrl.replace("http", "ws")}/karaoke_queue`);

    socket.on("queue_updated", (data) => {
      callbacks.onQueueUpdate?.(data);
    });

    socket.on("song_started", (data) => {
      callbacks.onSongStarted?.(data);
    });

    socket.on("song_finished", (data) => {
      callbacks.onSongFinished?.(data);
    });

    return socket;
  }
}

// Usage examples
const queueService = new KaraokeQueueService();

// Get current queue
const queue = await queueService.getQueue();
console.log("Current queue:", queue);

// Add to queue
await queueService.addToQueue("John Doe", "song-id-123");

// Real-time queue monitoring
const queueSocket = queueService.connectToQueueUpdates({
  onQueueUpdate: (queue) => {
    console.log("Queue updated:", queue);
    updateQueueUI(queue);
  },
  onSongStarted: (song) => {
    console.log("Song started:", song);
    showNowPlaying(song);
  },
  onSongFinished: (song) => {
    console.log("Song finished:", song);
    hideNowPlaying();
  },
});
```

## 🚀 Complete Application Example

### React Component with API Integration

```javascript
import React, { useState, useEffect } from "react";

function KaraokeApp() {
  const [songs, setSongs] = useState([]);
  const [queue, setQueue] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);

  const songService = new SongService();
  const queueService = new KaraokeQueueService();
  const jobsService = new JobsService();

  useEffect(() => {
    loadInitialData();
    setupRealTimeUpdates();
  }, []);

  async function loadInitialData() {
    try {
      const [songsData, queueData, jobsData] = await Promise.all([
        songService.getAllSongs(),
        queueService.getQueue(),
        jobsService.getAllJobs(),
      ]);

      setSongs(songsData);
      setQueue(queueData);
      setJobs(jobsData);
    } catch (error) {
      console.error("Failed to load data:", error);
    } finally {
      setLoading(false);
    }
  }

  function setupRealTimeUpdates() {
    // Job updates
    jobsService.connectToJobUpdates({
      onJobUpdate: (job) => {
        setJobs((prev) => prev.map((j) => (j.id === job.id ? job : j)));
      },
      onJobsList: (jobsList) => {
        setJobs(jobsList);
      },
    });

    // Queue updates
    queueService.connectToQueueUpdates({
      onQueueUpdate: (queueData) => {
        setQueue(queueData);
      },
    });
  }

  async function addSongToQueue(songId, singerName) {
    try {
      await queueService.addToQueue(singerName, songId);
      // Queue will update via WebSocket
    } catch (error) {
      console.error("Failed to add to queue:", error);
    }
  }

  async function searchAndAdd(query) {
    try {
      const results = await songService.searchSongs(query);
      if (results.length > 0) {
        const song = results[0];
        await addSongToQueue(song.id, "Current User");
      }
    } catch (error) {
      console.error("Search failed:", error);
    }
  }

  if (loading) return <div>Loading...</div>;

  return (
    <div className="karaoke-app">
      <h1>Open Karaoke Studio</h1>

      <div className="search-section">
        <input
          type="text"
          placeholder="Search songs..."
          onKeyPress={(e) => {
            if (e.key === "Enter") {
              searchAndAdd(e.target.value);
              e.target.value = "";
            }
          }}
        />
      </div>

      <div className="content">
        <div className="songs-list">
          <h2>Song Library ({songs.length})</h2>
          {songs.map((song) => (
            <div key={song.id} className="song-card">
              <h3>{song.title}</h3>
              <p>{song.artist}</p>
              <button onClick={() => addSongToQueue(song.id, "Current User")}>
                Add to Queue
              </button>
            </div>
          ))}
        </div>

        <div className="queue">
          <h2>Karaoke Queue ({queue.length})</h2>
          {queue.map((item, index) => (
            <div key={item.id} className="queue-item">
              <span>
                {index + 1}. {item.singer_name}
              </span>
              <button onClick={() => queueService.removeFromQueue(item.id)}>
                Remove
              </button>
            </div>
          ))}
        </div>

        <div className="jobs">
          <h2>Processing Jobs ({jobs.length})</h2>
          {jobs.map((job) => (
            <div key={job.id} className="job-item">
              <span>
                {job.song_title} - {job.status}
              </span>
              {job.status === "processing" && (
                <button onClick={() => jobsService.cancelJob(job.id)}>
                  Cancel
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default KaraokeApp;
```

## 🛠️ Error Handling & Best Practices

### Robust Error Handling

```javascript
class ApiClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
    this.retryAttempts = 3;
    this.retryDelay = 1000;
  }

  async requestWithRetry(path, options = {}) {
    let lastError;

    for (let attempt = 1; attempt <= this.retryAttempts; attempt++) {
      try {
        const response = await fetch(`${this.baseUrl}${path}`, {
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          ...options,
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.error || `HTTP ${response.status}`);
        }

        return response.json();
      } catch (error) {
        lastError = error;

        if (attempt < this.retryAttempts) {
          console.warn(
            `Request failed (attempt ${attempt}), retrying...`,
            error.message
          );
          await new Promise((resolve) =>
            setTimeout(resolve, this.retryDelay * attempt)
          );
        }
      }
    }

    throw lastError;
  }

  async safeRequest(path, options = {}) {
    try {
      return await this.requestWithRetry(path, options);
    } catch (error) {
      console.error(`API request failed: ${path}`, error);
      throw error;
    }
  }
}

// Usage with error boundaries
async function safeApiCall(apiCall, fallback = null) {
  try {
    return await apiCall();
  } catch (error) {
    console.error("API call failed:", error);
    return fallback;
  }
}

// Example usage
const songs = await safeApiCall(
  () => songService.getAllSongs(),
  [] // fallback to empty array
);
```

This JavaScript API integration guide provides comprehensive examples for all endpoints and real-time features available in the Open Karaoke Studio API, with modern patterns and robust error handling.
