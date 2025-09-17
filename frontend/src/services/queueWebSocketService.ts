/**
 * WebSocket service for real-time karaoke queue updates using native WebSockets (FastAPI)
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

interface QueueWebSocketEvents {
  queue_updated: (data: { items: QueueItem[] }) => void;
  queue_joined: (data: { room: string }) => void;
  queue_left: (data: { room: string }) => void;
}

class QueueWebSocketService {
  private websocket: WebSocket | null = null;
  private listeners: Map<string, Set<(data: unknown) => void>> = new Map();
  private isConnected = false;
  private maxReconnectAttempts = 5;
  private reconnectAttempts = 0;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private currentSessionId: string | null = null;

  constructor() {
    // Don't initialize connection immediately - wait for session
  }

  private initializeConnection() {
    try {
      let socketUrl: string;

      if (import.meta.env.DEV) {
        // Development mode - use the current host to leverage Vite proxy
        if (this.currentSessionId) {
          socketUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/session/${this.currentSessionId}/queue`;
          console.log("Development mode - using session-specific queue WebSocket:", socketUrl);
        } else {
          socketUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/queue`;
          console.log("Development mode - using global queue WebSocket (no session):", socketUrl);
        }
      } else {
        // Production mode - use direct URLs
        const backendUrl = import.meta.env.VITE_BACKEND_URL || 
                          `${window.location.protocol}//${window.location.host}`;
        if (this.currentSessionId) {
          socketUrl = `${backendUrl.replace('http', 'ws')}/ws/session/${this.currentSessionId}/queue`;
          console.log("Production mode - using session-specific queue WebSocket:", socketUrl);
        } else {
          socketUrl = `${backendUrl.replace('http', 'ws')}/ws/queue`;
          console.log("Production mode - using global queue WebSocket (no session):", socketUrl);
        }
      }

      console.log("Attempting to connect to queue WebSocket at:", socketUrl);
      
      this.websocket = new WebSocket(socketUrl);
      this.setupEventHandlers();
      
    } catch (error) {
      console.error("Failed to initialize queue WebSocket connection:", error);
      this.scheduleReconnect();
    }
  }

  private setupEventHandlers() {
    if (!this.websocket) return;

    this.websocket.onopen = () => {
      console.log("Connected to FastAPI queue WebSocket");
      this.isConnected = true;
      this.reconnectAttempts = 0;

      // Automatically join queue room
      this.send({ type: "join_queue_room" });
    };

    this.websocket.onclose = (event) => {
      console.log("Disconnected from FastAPI queue WebSocket:", event.code, event.reason);
      this.isConnected = false;
      this.websocket = null;
      
      // Attempt to reconnect if it wasn't a manual disconnect
      if (event.code !== 1000) { // 1000 = normal closure
        this.scheduleReconnect();
      }
    };

    this.websocket.onerror = (error) => {
      console.error("FastAPI queue WebSocket connection error:", error);
      this.isConnected = false;
    };

    this.websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("FastAPI queue WebSocket received:", data);
        
        switch (data.type) {
          case "queue_joined":
            console.log("Joined queue room:", data.room);
            this.emit("queue_joined", data);
            break;
            
          case "queue_left":
            console.log("Left queue room:", data.room);
            this.emit("queue_left", data);
            break;
            
          case "queue_updated":
            console.log("Queue updated:", data.items?.length || 0, "items");
            this.emit("queue_updated", data);
            break;
            
          case "error":
            console.error("Queue WebSocket error:", data.message);
            break;
            
          default:
            console.log("Unknown queue message type:", data.type);
        }
      } catch (error) {
        console.error("Error parsing FastAPI queue WebSocket message:", error);
      }
    };
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error("Max queue WebSocket reconnection attempts reached");
      return;
    }

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }

    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 5000);
    console.log(`Scheduling queue WebSocket reconnect in ${delay}ms (attempt ${this.reconnectAttempts + 1}/${this.maxReconnectAttempts})`);
    
    this.reconnectTimeout = setTimeout(() => {
      this.reconnectAttempts++;
      this.initializeConnection();
    }, delay);
  }

  private send(message: Record<string, unknown>) {
    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
      this.websocket.send(JSON.stringify(message));
    } else {
      console.warn("Cannot send queue message: WebSocket not connected");
    }
  }

  private emit(eventName: string, data: unknown) {
    const eventListeners = this.listeners.get(eventName);
    if (eventListeners) {
      eventListeners.forEach((listener) => {
        try {
          listener(data);
        } catch (error) {
          console.error(`Error in queue ${eventName} listener:`, error);
        }
      });
    }
  }

  /**
   * Add an event listener for queue events
   */
  on<T extends keyof QueueWebSocketEvents>(
    event: T,
    listener: QueueWebSocketEvents[T],
  ) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    // Cast the listener to match our storage type
    this.listeners.get(event)!.add(listener as (data: unknown) => void);

    // Return cleanup function
    return () => {
      this.off(event, listener);
    };
  }

  /**
   * Remove an event listener
   */
  off<T extends keyof QueueWebSocketEvents>(
    event: T,
    listener: QueueWebSocketEvents[T],
  ) {
    const eventListeners = this.listeners.get(event);
    if (eventListeners) {
      eventListeners.delete(listener as (data: unknown) => void);
      if (eventListeners.size === 0) {
        this.listeners.delete(event);
      }
    }
  }

  /**
   * Check if WebSocket is connected
   */
  isConnectionActive(): boolean {
    return this.isConnected && this.websocket?.readyState === WebSocket.OPEN;
  }

  /**
   * Join queue room for updates
   */
  joinQueueRoom() {
    this.send({ type: "join_queue_room" });
  }

  /**
   * Leave queue room
   */
  leaveQueueRoom() {
    this.send({ type: "leave_queue_room" });
  }

  /**
   * Request queue update
   */
  requestQueueUpdate() {
    this.send({ type: "request_queue_update" });
  }

  /**
   * Update connection when session changes
   */
  updateSession(sessionId: string | null) {
    console.log("Updating queue WebSocket for new session:", sessionId);
    this.currentSessionId = sessionId;
    this.disconnect();
    this.reconnectAttempts = 0;
    
    // Only initialize if we have a session ID
    if (sessionId) {
      this.initializeConnection();
    }
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
      this.send({ type: "leave_queue_room" });
      this.websocket.close(1000, "Manual disconnect"); // Normal closure
      this.websocket = null;
    }
    this.isConnected = false;
    this.listeners.clear();
    this.reconnectAttempts = 0;
  }

  /**
   * Manually reconnect the WebSocket
   */
  reconnect() {
    this.disconnect();
    this.reconnectAttempts = 0;
    this.initializeConnection();
  }
}

// Create singleton instance
export const queueWebSocketService = new QueueWebSocketService();

export default QueueWebSocketService;