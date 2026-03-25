import { http, HttpResponse } from "msw";

// Default mock data
export const mockSong = {
  id: "test-song-123",
  title: "Test Song",
  artist: "Test Artist",
  duration: 180,
  status: "ready",
  createdAt: "2024-01-01T00:00:00Z",
  updatedAt: "2024-01-01T00:00:00Z",
  syncedLyrics: null,
  plainLyrics: "Test lyrics here",
};

export const mockQueueItem = {
  id: "queue-item-1",
  songId: "test-song-123",
  singerName: "Test Singer",
  position: 0,
  status: "pending",
  song: mockSong,
};

export const mockSession = {
  id: "test-session-123",
  name: "Test Session",
  createdAt: "2024-01-01T00:00:00Z",
};

// API handlers
export const handlers = [
  // Songs endpoints
  http.get("/api/songs", () => {
    return HttpResponse.json({
      songs: [mockSong],
      total: 1,
      page: 1,
      pageSize: 20,
    });
  }),

  http.get("/api/songs/:songId", ({ params }) => {
    return HttpResponse.json({
      ...mockSong,
      id: params.songId,
    });
  }),

  http.get("/api/songs/:songId/download/instrumental", () => {
    // Return empty audio data
    return new HttpResponse(new ArrayBuffer(1024), {
      headers: {
        "Content-Type": "audio/mpeg",
      },
    });
  }),

  http.get("/api/songs/:songId/download/vocals", () => {
    // Return empty audio data
    return new HttpResponse(new ArrayBuffer(1024), {
      headers: {
        "Content-Type": "audio/mpeg",
      },
    });
  }),

  // Queue endpoints
  http.get("/api/queue", () => {
    return HttpResponse.json({
      items: [mockQueueItem],
      currentItem: null,
    });
  }),

  http.post("/api/queue", async ({ request }) => {
    const body = (await request.json()) as {
      songId: string;
      singerName: string;
    };
    return HttpResponse.json({
      ...mockQueueItem,
      songId: body.songId,
      singerName: body.singerName,
    });
  }),

  http.delete("/api/queue/:itemId", () => {
    return new HttpResponse(null, { status: 204 });
  }),

  // Session endpoints
  http.get("/api/sessions/:sessionId", ({ params }) => {
    return HttpResponse.json({
      ...mockSession,
      id: params.sessionId,
    });
  }),

  http.post("/api/sessions", async ({ request }) => {
    const body = (await request.json()) as { name?: string };
    return HttpResponse.json({
      ...mockSession,
      name: body.name || "New Session",
    });
  }),

  // Lyrics endpoints
  http.get("/api/songs/:songId/lyrics", () => {
    return HttpResponse.json({
      syncedLyrics: null,
      plainLyrics: "Test lyrics content",
    });
  }),
];
