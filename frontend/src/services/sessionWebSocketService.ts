/**
 * Unified Session WebSocket Service
 * Handles all session-related WebSocket communication:
 * - Performance controls and player state
 * - Queue management 
 * - Real-time session synchronization
 */

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
}

type ControlValue = number | string | boolean;

interface SessionWebSocketEvents {
  // Session connection events
  session_connected: (data: { session_id: string; device_id: string; performance_state: PerformanceState }) => void;
  session_error: (data: { error: string }) => void;
  
  // Performance control events
  performance_state: (data: { state: PerformanceState }) => void;
  control_updated: (data: { control: string; value: ControlValue }) => void;
  playback_play: () => void;
  playback_pause: () => void;
  song_loaded: (data: { state: PerformanceState }) => void;
  song_ready: (data: { state: PerformanceState }) => void;
  
  // Queue events
  queue_joined: (data: { room: string }) => void;
  queue_updated: (data: { items?: QueueItem[]; trigger?: string }) => void;
}

type EventData = PerformanceState | { error: string } | { room: string } | { items?: QueueItem[]; trigger?: string } | { control: string; value: ControlValue } | undefined;

class SessionWebSocketService {
  private websocket: WebSocket | null = null;
  private listeners: Map<string, Set<(data: EventData) => void>> = new Map();
  private isConnected = false;
  private maxReconnectAttempts = 5;
  private reconnectAttempts = 0;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private currentSessionId: string | null = null;
  private deviceId: string | null = null;

  constructor() {
    // Don't initialize connection immediately - wait for session
  }

  private initializeConnection(sessionId: string) {
    try {
      let socketUrl: string;

      if (import.meta.env.DEV) {
        // Development mode - use the current host to leverage Vite proxy
        socketUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/session/${sessionId}`;
        console.log("Development mode - using unified session WebSocket:", socketUrl);
      } else {
        // Production mode - use direct URLs
        const backendUrl = import.meta.env.VITE_BACKEND_URL || 
                          `${window.location.protocol}//${window.location.host}`;
        socketUrl = `${backendUrl.replace('http', 'ws')}/ws/session/${sessionId}`;
        console.log("Production mode - using unified session WebSocket:", socketUrl);
      }

      console.log("Attempting to connect to unified session WebSocket at:", socketUrl);
      
      this.websocket = new WebSocket(socketUrl);
      this.setupEventHandlers();
      
    } catch (error) {
      console.error("Failed to initialize unified session WebSocket connection:", error);
      this.scheduleReconnect();
    }
  }

  private setupEventHandlers() {
    if (!this.websocket) return;

    this.websocket.onopen = () => {
      console.log("Connected to unified session WebSocket");
      this.isConnected = true;
      this.reconnectAttempts = 0;

      // Initialize both performance and queue functionality
      this.send({ type: "join_performance" });
      this.send({ type: "join_queue_room" });
    };

    this.websocket.onclose = (event) => {
      console.log("Disconnected from unified session WebSocket:", event.code, event.reason);
      this.isConnected = false;
      this.websocket = null;
      
      // Attempt to reconnect if it wasn't a manual disconnect
      if (event.code !== 1000) { // 1000 = normal closure
        this.scheduleReconnect();
      }
    };

    this.websocket.onerror = (error) => {
      console.error("Unified session WebSocket connection error:", error);
      this.isConnected = false;
    };

    this.websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("Unified session WebSocket received:", data);
        
        // Emit the event to all registered listeners
        this.emit(data.type, data);
        
      } catch (error) {
        console.error("Error parsing unified session WebSocket message:", error);
      }
    };
  }

  private scheduleReconnect() {
    if (!this.currentSessionId) {
      console.log("No session ID - not scheduling reconnect");
      return;
    }

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error("Max unified session WebSocket reconnection attempts reached");
      return;
    }

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }

    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 5000);
    console.log(`Scheduling unified session WebSocket reconnect in ${delay}ms (attempt ${this.reconnectAttempts + 1}/${this.maxReconnectAttempts})`);
    
    this.reconnectTimeout = setTimeout(() => {
      this.reconnectAttempts++;
      if (this.currentSessionId) {
        this.initializeConnection(this.currentSessionId);
      }
    }, delay);
  }

  private send(message: Record<string, unknown>) {
    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
      this.websocket.send(JSON.stringify(message));
    } else {
      console.warn("Cannot send unified session message: WebSocket not connected");
    }
  }

  private emit(eventName: string, data: EventData) {
    const eventListeners = this.listeners.get(eventName);
    if (eventListeners) {
      eventListeners.forEach((listener) => {
        try {
          listener(data);
        } catch (error) {
          console.error(`Error in unified session ${eventName} listener:`, error);
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
   */
  connectToSession(sessionId: string) {
    console.log("Connecting to unified session WebSocket for session:", sessionId);
    this.currentSessionId = sessionId;
    this.disconnect(); // Clean up any existing connection
    this.reconnectAttempts = 0;
    this.initializeConnection(sessionId);
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
      value
    });
  }

  /**
   * Update player state (playback position, duration, etc.)
   */
  updatePlayerState(state: { isPlaying?: boolean; currentTime?: number; duration?: number }) {
    this.send({
      type: "update_player_state",
      ...state
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
      isPlaying: false
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
      isReady: true
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
    this.deviceId = null;
  }

  /**
   * Manually reconnect the WebSocket
   */
  reconnect() {
    if (this.currentSessionId) {
      this.disconnect();
      this.reconnectAttempts = 0;
      this.initializeConnection(this.currentSessionId);
    }
  }
}

// Create singleton instance
export const sessionWebSocketService = new SessionWebSocketService();

export default SessionWebSocketService;