/**
 * Unified Session WebSocket Service
 * Handles all session-related WebSocket communication:
 * - Performance controls and player state
 * - Queue management
 * - Real-time session synchronization
 */

import { createLogger } from "@/lib/logger";

const logger = createLogger("websocket:session");

interface QueueItem {
  id: string;
  songId: string;
  singer: string;
  position: number;
  addedAt?: string;
  song: {
    id: string;
    title: string;
    artist: string;
    album?: string;
    duration?: number;
    coverArt?: string;
    syncedLyrics?: string;
    plainLyrics?: string;
  };
}

interface PerformanceState {
  vocal_volume: number;
  instrumental_volume: number;
  lyrics_size: "small" | "medium" | "large";
  lyrics_offset: number;
  current_time: number;
  duration: number;
  is_playing: boolean;
  current_song_id?: string | null;
  is_ready?: boolean;
  playback_speed: number;
}

type ControlValue = number | string | boolean;

interface SessionWebSocketEvents {
  // Session connection events
  session_connected: (data: {
    session_id: string;
    device_id: string;
    is_host: boolean;
    performance_state: PerformanceState;
  }) => void;
  session_error: (data: { error: string }) => void;
  session_ended: (data: { reason: string }) => void;

  // Performance control events
  performance_state: (data: { state: PerformanceState }) => void;
  control_updated: (data: { control: string; value: ControlValue }) => void;
  playback_play: () => void;
  playback_pause: () => void;
  song_loaded: (data: { state: PerformanceState }) => void;
  song_ready: (data: { state: PerformanceState }) => void;

  // Queue events
  queue_joined: (data: { room: string }) => void;
  queue_updated: (data: {
    current?: QueueItem | null;
    upcoming?: QueueItem[];
    items?: QueueItem[];
    trigger?: string;
  }) => void;

  // UI control events (performer → host)
  toggle_fullscreen: () => void;
}

type EventData =
  | PerformanceState
  | { error: string }
  | { room: string }
  | {
      current?: QueueItem | null;
      upcoming?: QueueItem[];
      items?: QueueItem[];
      trigger?: string;
    }
  | { control: string; value: ControlValue }
  | undefined;

class SessionWebSocketService {
  private websocket: WebSocket | null = null;
  private listeners: Map<string, Set<(data: EventData) => void>> = new Map();
  private isConnected = false;
  private maxReconnectAttempts = 5;
  private reconnectAttempts = 0;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private currentSessionId: string | null = null;
  private deviceId: string | null = null;
  private hostDeviceId: string | null = null; // REST API device ID for host identification

  constructor() {
    // Don't initialize connection immediately - wait for session
  }

  private initializeConnection(sessionId: string, url: string) {
    try {
      logger.debug(
        "Attempting to connect to unified session WebSocket at:",
        url,
      );

      this.websocket = new WebSocket(url);
      this.setupEventHandlers();
    } catch (error) {
      logger.error(
        "Failed to initialize unified session WebSocket connection:",
        error,
      );
      this.scheduleReconnect();
    }
  }

  private setupEventHandlers() {
    if (!this.websocket) return;

    this.websocket.onopen = () => {
      logger.debug("Connected to unified session WebSocket");
      this.isConnected = true;
      this.reconnectAttempts = 0;

      // Initialize both performance and queue functionality
      this.send({ type: "join_performance" });
      this.send({ type: "join_queue_room" });
    };

    this.websocket.onclose = (event) => {
      logger.debug(
        "Disconnected from unified session WebSocket:",
        event.code,
        event.reason,
      );
      this.isConnected = false;
      this.websocket = null;

      // Attempt to reconnect if it wasn't a manual disconnect
      if (event.code !== 1000) {
        // 1000 = normal closure
        this.scheduleReconnect();
      }
    };

    this.websocket.onerror = (error) => {
      logger.error("Unified session WebSocket connection error:", error);
      this.isConnected = false;
    };

    this.websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        logger.debug("Unified session WebSocket received:", data);

        // Hydrate the ephemeral WebSocket device ID from the server's greeting
        if (data.type === "session_connected" && data.device_id) {
          this.deviceId = data.device_id;
        }

        // Emit the event to all registered listeners
        this.emit(data.type, data);
      } catch (error) {
        logger.error("Error parsing unified session WebSocket message:", error);
      }
    };
  }

  private scheduleReconnect() {
    if (!this.currentSessionId) {
      logger.debug("No session ID - not scheduling reconnect");
      return;
    }

    // Never give up reconnecting for personal use - just slow down the attempts
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }

    // Cap at 30 seconds, but never stop trying
    const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), 30000);
    logger.debug(
      `Scheduling unified session WebSocket reconnect in ${delay / 1000}s (attempt ${this.reconnectAttempts + 1})`,
    );

    this.reconnectTimeout = setTimeout(() => {
      this.reconnectAttempts++;
      if (this.currentSessionId) {
        // Rebuild the WebSocket URL with device_id query parameter if host
        let baseSocketUrl: string;
        if (import.meta.env.DEV) {
          baseSocketUrl = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws/session/${this.currentSessionId}`;
        } else {
          const backendUrl =
            import.meta.env.VITE_BACKEND_URL ||
            `${window.location.protocol}//${window.location.host}`;
          baseSocketUrl = `${backendUrl.replace("http", "ws")}/ws/session/${this.currentSessionId}`;
        }

        const socketUrl = this.hostDeviceId
          ? `${baseSocketUrl}?device_id=${encodeURIComponent(this.hostDeviceId)}`
          : baseSocketUrl;

        this.initializeConnection(this.currentSessionId, socketUrl);
      }
    }, delay);
  }

  private send(message: Record<string, unknown>) {
    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
      this.websocket.send(JSON.stringify(message));
    } else {
      logger.warn(
        "Cannot send unified session message: WebSocket not connected",
      );
    }
  }

  private emit(eventName: string, data: EventData) {
    const eventListeners = this.listeners.get(eventName);
    if (eventListeners) {
      eventListeners.forEach((listener) => {
        try {
          listener(data);
        } catch (error) {
          logger.error(
            `Error in unified session ${eventName} listener:`,
            error,
          );
        }
      });
    }
  }

  /**
   * Add an event listener for session events
   */
  on<T extends keyof SessionWebSocketEvents>(
    event: T,
    listener: SessionWebSocketEvents[T],
  ) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    // Cast the listener to match our storage type
    this.listeners.get(event)!.add(listener as (data: EventData) => void);

    // Return cleanup function
    return () => {
      this.off(event, listener);
    };
  }

  /**
   * Remove an event listener
   */
  off<T extends keyof SessionWebSocketEvents>(
    event: T,
    listener: SessionWebSocketEvents[T],
  ) {
    const eventListeners = this.listeners.get(event);
    if (eventListeners) {
      eventListeners.delete(listener as (data: EventData) => void);
      if (eventListeners.size === 0) {
        this.listeners.delete(event);
      }
    }
  }

  /**
   * Connect to a session
   * @param sessionId The session ID to connect to
   * @param hostDeviceId Optional: The REST API device ID if this device is the host
   */
  connectToSession(sessionId: string, hostDeviceId?: string) {
    logger.debug(
      "Connecting to unified session WebSocket for session:",
      sessionId,
      hostDeviceId ? "(as host)" : "(as performer)",
    );
    this.disconnect(); // Clean up any existing connection first
    this.currentSessionId = sessionId;
    this.hostDeviceId = hostDeviceId || null;
    this.reconnectAttempts = 0;

    // Build WebSocket URL with device_id query parameter if host
    let baseSocketUrl: string;
    if (import.meta.env.DEV) {
      // Development mode - use the current host to leverage Vite proxy
      baseSocketUrl = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws/session/${sessionId}`;
    } else {
      // Production mode - use direct URLs
      const backendUrl =
        import.meta.env.VITE_BACKEND_URL ||
        `${window.location.protocol}//${window.location.host}`;
      baseSocketUrl = `${backendUrl.replace("http", "ws")}/ws/session/${sessionId}`;
    }

    // Add device_id query parameter if this is the host
    const socketUrl = hostDeviceId
      ? `${baseSocketUrl}?device_id=${encodeURIComponent(hostDeviceId)}`
      : baseSocketUrl;

    this.initializeConnection(sessionId, socketUrl);
  }

  /**
   * Check if WebSocket is connected
   */
  isConnectionActive(): boolean {
    return this.isConnected && this.websocket?.readyState === WebSocket.OPEN;
  }

  /**
   * Get current device ID (set after connection)
   */
  getDeviceId(): string | null {
    return this.deviceId;
  }

  // === PERFORMANCE CONTROL METHODS ===

  /**
   * Update performance control (volume, lyrics, etc.)
   */
  updatePerformanceControl(control: string, value: ControlValue) {
    this.send({
      type: "update_performance_control",
      control,
      value,
    });
  }

  /**
   * Update player state (playback position, duration, etc.)
   */
  updatePlayerState(state: {
    isPlaying?: boolean;
    currentTime?: number;
    duration?: number;
  }) {
    this.send({
      type: "update_player_state",
      ...state,
    });
  }

  /**
   * Send play command
   */
  playback() {
    this.send({ type: "playback_play" });
  }

  /**
   * Send pause command
   */
  pause() {
    this.send({ type: "playback_pause" });
  }

  /**
   * Notify that a song has been loaded
   */
  songLoaded(songId: string, duration: number) {
    this.send({
      type: "song_loaded",
      songId,
      duration,
      currentTime: 0,
      isPlaying: false,
    });
  }

  /**
   * Notify that a song is ready to play
   */
  songReady(songId: string, duration: number) {
    this.send({
      type: "song_ready",
      songId,
      duration,
      currentTime: 0,
      isPlaying: false,
      isReady: true,
    });
  }

  // === QUEUE MANAGEMENT METHODS ===

  /**
   * Request queue update
   */
  requestQueueUpdate() {
    this.send({ type: "request_queue_update" });
  }

  /**
   * Notify about queue changes (called after API mutations)
   */
  notifyQueueChanged() {
    this.send({ type: "queue_changed" });
  }

  /**
   * Tell the host device to toggle fullscreen
   */
  toggleFullscreen() {
    this.send({ type: "toggle_fullscreen" });
  }

  /**
   * Manually disconnect the WebSocket
   */
  disconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.websocket) {
      this.websocket.close(1000, "Manual disconnect"); // Normal closure
      this.websocket = null;
    }

    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.currentSessionId = null;
    this.deviceId = null; // cleared until next session_connected
    this.hostDeviceId = null;
  }

  /**
   * Manually reconnect the WebSocket
   */
  reconnect() {
    if (this.currentSessionId) {
      const sessionId = this.currentSessionId;
      const hostDeviceId = this.hostDeviceId;
      this.disconnect();
      this.connectToSession(sessionId, hostDeviceId || undefined);
    }
  }
}

// Create singleton instance
export const sessionWebSocketService = new SessionWebSocketService();

export default SessionWebSocketService;
