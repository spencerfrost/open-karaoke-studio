import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { act } from "@testing-library/react";
import { useKaraokePlayerStore } from "./useKaraokePlayerStore";
import { sessionWebSocketService } from "../services/sessionWebSocketService";

// Mock the sessionWebSocketService
const mockListeners = new Map<string, Set<(data: unknown) => void>>();

vi.mock("../services/sessionWebSocketService", () => ({
  sessionWebSocketService: {
    on: vi.fn((event: string, listener: (data: unknown) => void) => {
      if (!mockListeners.has(event)) {
        mockListeners.set(event, new Set());
      }
      mockListeners.get(event)!.add(listener);
      return () => mockListeners.get(event)?.delete(listener);
    }),
    off: vi.fn(),
    isConnectionActive: vi.fn(() => false),
    updatePerformanceControl: vi.fn(),
    updatePlayerState: vi.fn(),
    playback: vi.fn(),
    pause: vi.fn(),
    songLoaded: vi.fn(),
    songReady: vi.fn(),
  },
}));

// Helper to emit events to listeners
function emitMockEvent(event: string, data: unknown) {
  mockListeners.get(event)?.forEach((listener) => listener(data));
}

// Helper to get initial state values (non-functions only)
function getState() {
  const state = useKaraokePlayerStore.getState();
  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(state)) {
    if (typeof value !== "function") {
      result[key] = value;
    }
  }
  return result;
}

describe("useKaraokePlayerStore", () => {
  beforeEach(() => {
    // Reset the store to initial state before each test
    act(() => {
      useKaraokePlayerStore.setState({
        songId: null,
        instrumentalUrl: "",
        vocalUrl: "",
        isReady: false,
        isLoading: false,
        duration: 0,
        error: null,
        songTitle: null,
        songArtist: null,
        isPlaying: false,
        currentTime: 0,
        songEnded: false,
        vocalVolume: 0,
        instrumentalVolume: 1.0,
        lyricsSize: "medium",
        lyricsOffset: 0,
        autoScrollEnabled: true,
        connected: false,
        miniPlayerEnabled: true,
        miniPlayerPosition: { x: 24, y: 24 },
        miniPlayerDismissed: false,
      });
    });
    vi.clearAllMocks();
    mockListeners.clear();
  });

  afterEach(() => {
    mockListeners.clear();
  });

  describe("initial state", () => {
    it("should have correct default values", () => {
      const state = getState();

      expect(state.songId).toBeNull();
      expect(state.isReady).toBe(false);
      expect(state.isLoading).toBe(false);
      expect(state.isPlaying).toBe(false);
      expect(state.currentTime).toBe(0);
      expect(state.duration).toBe(0);
      expect(state.vocalVolume).toBe(0);
      expect(state.instrumentalVolume).toBe(1.0);
      expect(state.lyricsSize).toBe("medium");
      expect(state.lyricsOffset).toBe(0);
      expect(state.autoScrollEnabled).toBe(true);
      expect(state.connected).toBe(false);
      expect(state.miniPlayerEnabled).toBe(true);
      expect(state.miniPlayerDismissed).toBe(false);
    });
  });

  describe("volume controls", () => {
    it("should set vocal volume and clamp to 0-1 range", () => {
      const store = useKaraokePlayerStore.getState();

      act(() => {
        store.setVocalVolume(0.5);
      });
      expect(useKaraokePlayerStore.getState().vocalVolume).toBe(0.5);

      // Test clamping above 1
      act(() => {
        store.setVocalVolume(1.5);
      });
      expect(useKaraokePlayerStore.getState().vocalVolume).toBe(1);

      // Test clamping below 0
      act(() => {
        store.setVocalVolume(-0.5);
      });
      expect(useKaraokePlayerStore.getState().vocalVolume).toBe(0);
    });

    it("should set instrumental volume and clamp to 0-1 range", () => {
      const store = useKaraokePlayerStore.getState();

      act(() => {
        store.setInstrumentalVolume(0.7);
      });
      expect(useKaraokePlayerStore.getState().instrumentalVolume).toBe(0.7);

      // Test clamping above 1
      act(() => {
        store.setInstrumentalVolume(2.0);
      });
      expect(useKaraokePlayerStore.getState().instrumentalVolume).toBe(1);

      // Test clamping below 0
      act(() => {
        store.setInstrumentalVolume(-1);
      });
      expect(useKaraokePlayerStore.getState().instrumentalVolume).toBe(0);
    });

    it("should send WebSocket update when setting volume", () => {
      const store = useKaraokePlayerStore.getState();

      act(() => {
        store.setVocalVolume(0.8);
      });

      expect(
        sessionWebSocketService.updatePerformanceControl,
      ).toHaveBeenCalledWith("vocal_volume", 0.8);
    });
  });

  describe("lyrics controls", () => {
    it("should set lyrics size", () => {
      const store = useKaraokePlayerStore.getState();

      act(() => {
        store.setLyricsSize("large");
      });
      expect(useKaraokePlayerStore.getState().lyricsSize).toBe("large");

      act(() => {
        store.setLyricsSize("small");
      });
      expect(useKaraokePlayerStore.getState().lyricsSize).toBe("small");
    });

    it("should set lyrics offset", () => {
      const store = useKaraokePlayerStore.getState();

      act(() => {
        store.setLyricsOffset(2.5);
      });
      expect(useKaraokePlayerStore.getState().lyricsOffset).toBe(2.5);

      act(() => {
        store.setLyricsOffset(-1.5);
      });
      expect(useKaraokePlayerStore.getState().lyricsOffset).toBe(-1.5);
    });

    it("should toggle auto-scroll without WebSocket sync", () => {
      const store = useKaraokePlayerStore.getState();

      act(() => {
        store.setAutoScrollEnabled(false);
      });
      expect(useKaraokePlayerStore.getState().autoScrollEnabled).toBe(false);

      // Auto-scroll is local-only, should not trigger WebSocket update
      expect(
        sessionWebSocketService.updatePerformanceControl,
      ).not.toHaveBeenCalledWith("auto_scroll_enabled", expect.anything());
    });
  });

  describe("setSongId", () => {
    it("should set song ID and construct URLs", () => {
      const store = useKaraokePlayerStore.getState();

      act(() => {
        store.setSongId("test-song-123", 180);
      });

      const state = useKaraokePlayerStore.getState();
      expect(state.songId).toBe("test-song-123");
      expect(state.instrumentalUrl).toBe(
        "/api/songs/test-song-123/download/instrumental",
      );
      expect(state.vocalUrl).toBe("/api/songs/test-song-123/download/vocals");
      expect(state.duration).toBe(180);
      expect(state.isReady).toBe(false);
      expect(state.currentTime).toBe(0);
      expect(state.isPlaying).toBe(false);
    });

    it("should reset playback state when changing songs", () => {
      // First set up a song as if it was playing
      act(() => {
        useKaraokePlayerStore.setState({
          songId: "old-song",
          currentTime: 60,
          isPlaying: true,
          isReady: true,
        });
      });

      // Now change to a new song
      const store = useKaraokePlayerStore.getState();
      act(() => {
        store.setSongId("new-song", 200);
      });

      const state = useKaraokePlayerStore.getState();
      expect(state.songId).toBe("new-song");
      expect(state.currentTime).toBe(0);
      expect(state.isPlaying).toBe(false);
      expect(state.isReady).toBe(false);
    });

    it("should reset miniPlayerDismissed for new song", () => {
      // Dismiss mini player for current song
      act(() => {
        useKaraokePlayerStore.setState({
          songId: "old-song",
          miniPlayerDismissed: true,
        });
      });

      // Change to new song
      const store = useKaraokePlayerStore.getState();
      act(() => {
        store.setSongId("new-song");
      });

      expect(useKaraokePlayerStore.getState().miniPlayerDismissed).toBe(false);
    });
  });

  describe("mini-player", () => {
    it("should enable/disable mini-player", () => {
      const store = useKaraokePlayerStore.getState();

      act(() => {
        store.setMiniPlayerEnabled(false);
      });
      expect(useKaraokePlayerStore.getState().miniPlayerEnabled).toBe(false);

      act(() => {
        store.setMiniPlayerEnabled(true);
      });
      expect(useKaraokePlayerStore.getState().miniPlayerEnabled).toBe(true);
    });

    it("should update mini-player position", () => {
      const store = useKaraokePlayerStore.getState();

      act(() => {
        store.setMiniPlayerPosition({ x: 100, y: 200 });
      });

      const state = useKaraokePlayerStore.getState();
      expect(state.miniPlayerPosition).toEqual({ x: 100, y: 200 });
    });

    it("should dismiss mini-player for current song", () => {
      const store = useKaraokePlayerStore.getState();

      act(() => {
        store.dismissMiniPlayer();
      });

      expect(useKaraokePlayerStore.getState().miniPlayerDismissed).toBe(true);
    });
  });

  describe("songEnded state", () => {
    it("should reset songEnded when resetSongEnded is called", () => {
      act(() => {
        useKaraokePlayerStore.setState({ songEnded: true });
      });

      const store = useKaraokePlayerStore.getState();
      act(() => {
        store.resetSongEnded();
      });

      expect(useKaraokePlayerStore.getState().songEnded).toBe(false);
    });
  });

  describe("WebSocket connection", () => {
    it("should set up WebSocket listeners on connect", () => {
      const store = useKaraokePlayerStore.getState();

      act(() => {
        store.connect();
      });

      // Should register listeners for various events
      expect(sessionWebSocketService.on).toHaveBeenCalledWith(
        "performance_state",
        expect.any(Function),
      );
      expect(sessionWebSocketService.on).toHaveBeenCalledWith(
        "control_updated",
        expect.any(Function),
      );
      expect(sessionWebSocketService.on).toHaveBeenCalledWith(
        "playback_play",
        expect.any(Function),
      );
      expect(sessionWebSocketService.on).toHaveBeenCalledWith(
        "playback_pause",
        expect.any(Function),
      );
      expect(sessionWebSocketService.on).toHaveBeenCalledWith(
        "session_connected",
        expect.any(Function),
      );
    });

    it("should set connected to true when session_connected event is received", () => {
      const store = useKaraokePlayerStore.getState();

      act(() => {
        store.connect();
      });

      expect(useKaraokePlayerStore.getState().connected).toBe(false);

      // Simulate session_connected event
      act(() => {
        emitMockEvent("session_connected", {
          session_id: "test-session",
          device_id: "test-device",
          is_host: true,
          performance_state: {},
        });
      });

      expect(useKaraokePlayerStore.getState().connected).toBe(true);
    });

    it("should set connected to false on disconnect", () => {
      act(() => {
        useKaraokePlayerStore.setState({ connected: true });
      });

      const store = useKaraokePlayerStore.getState();
      act(() => {
        store.disconnect();
      });

      expect(useKaraokePlayerStore.getState().connected).toBe(false);
    });
  });

  describe("updateFromWebSocket", () => {
    it("should update volume from WebSocket data", () => {
      const store = useKaraokePlayerStore.getState();

      act(() => {
        store.updateFromWebSocket({
          vocal_volume: 0.6,
          instrumental_volume: 0.8,
        });
      });

      const state = useKaraokePlayerStore.getState();
      expect(state.vocalVolume).toBe(0.6);
      expect(state.instrumentalVolume).toBe(0.8);
    });

    it("should update lyrics settings from WebSocket data", () => {
      const store = useKaraokePlayerStore.getState();

      act(() => {
        store.updateFromWebSocket({
          lyrics_size: "large",
          lyrics_offset: 1.5,
        });
      });

      const state = useKaraokePlayerStore.getState();
      expect(state.lyricsSize).toBe("large");
      expect(state.lyricsOffset).toBe(1.5);
    });

    it("should update playback state from WebSocket data", () => {
      const store = useKaraokePlayerStore.getState();

      act(() => {
        store.updateFromWebSocket({
          is_playing: true,
          current_time: 45.5,
          duration: 180,
        });
      });

      const state = useKaraokePlayerStore.getState();
      expect(state.isPlaying).toBe(true);
      expect(state.currentTime).toBe(45.5);
      expect(state.duration).toBe(180);
    });
  });
});
