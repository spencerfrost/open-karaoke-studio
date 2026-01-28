/**
 * WebSocket service for real-time job updates using native WebSockets (FastAPI)
 * Migrated from Socket.IO to native WebSocket for FastAPI compatibility
 */

interface JobData {
  id: string;
  progress?: number;
  status: string;
  error?: string;
  notes?: string;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
  filename?: string;
  task_id?: string;
  artist?: string;
  title?: string;
}

interface JobsWebSocketEvents {
  job_created: (data: JobData) => void;
  job_updated: (data: JobData) => void;
  job_completed: (data: JobData) => void;
  job_failed: (data: JobData) => void;
  job_cancelled: (data: JobData) => void;
  jobs_list: (data: { jobs: JobData[] }) => void;
}

class JobsWebSocketService {
  private websocket: WebSocket | null = null;
  private listeners: Map<string, Set<(data: unknown) => void>> = new Map();
  private isConnected = false;
  private maxReconnectAttempts = 5;
  private reconnectAttempts = 0;
  private reconnectTimeout: NodeJS.Timeout | null = null;

  constructor() {
    this.initializeConnection();
  }

  private initializeConnection() {
    try {
      // Use the WebSocket URL that goes through Vite proxy in development
      // or directly to FastAPI in production
      let socketUrl: string;

      if (import.meta.env.DEV) {
        // Development mode - use the current host to leverage Vite proxy (/ws -> localhost:5124)
        socketUrl = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws/jobs`;
        console.log(
          "Development mode - using Vite proxy for WebSocket:",
          socketUrl,
        );
      } else {
        // Production mode - use FastAPI WebSocket directly
        const backendUrl =
          import.meta.env.VITE_BACKEND_URL ||
          `${window.location.protocol}//${window.location.host}`;
        socketUrl = `${backendUrl.replace("http", "ws")}/ws/jobs`;
        console.log(
          "Production mode - using direct FastAPI WebSocket:",
          socketUrl,
        );
      }

      console.log("Attempting to connect to FastAPI WebSocket at:", socketUrl);

      this.websocket = new WebSocket(socketUrl);
      this.setupEventHandlers();
    } catch (error) {
      console.error("Failed to initialize WebSocket connection:", error);
      this.scheduleReconnect();
    }
  }

  private setupEventHandlers() {
    if (!this.websocket) return;

    this.websocket.onopen = () => {
      console.log("Connected to FastAPI jobs WebSocket");
      this.isConnected = true;
      this.reconnectAttempts = 0;

      // Subscribe to job updates
      this.send({ type: "subscribe_to_jobs" });
    };

    this.websocket.onclose = (event) => {
      console.log(
        "Disconnected from FastAPI jobs WebSocket:",
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
      console.error("FastAPI WebSocket connection error:", error);
      this.isConnected = false;
    };

    this.websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("FastAPI WebSocket received:", data);

        switch (data.type) {
          case "connected":
            console.log("FastAPI WebSocket connection confirmed");
            break;

          case "subscribed":
            console.log("Subscribed to job updates:", data);
            break;

          case "jobs_list":
            console.log("Received jobs list:", data);
            this.emit("jobs_list", { jobs: data.jobs });
            break;

          case "job_created":
            console.log("Received job_created event:", data.job);
            this.emit("job_created", data.job);
            break;

          case "job_updated":
            console.log("Received job_updated event:", data.job);
            this.emit("job_updated", data.job);
            break;

          case "job_completed":
            console.log("Received job_completed event:", data.job);
            this.emit("job_completed", data.job);
            break;

          case "job_failed":
            console.log("Received job_failed event:", data.job);
            this.emit("job_failed", data.job);
            break;

          case "job_cancelled":
            console.log("Received job_cancelled event:", data.job);
            this.emit("job_cancelled", data.job);
            break;

          case "error":
            console.error("WebSocket error:", data.message);
            break;

          default:
            console.log("Unknown message type:", data.type);
        }
      } catch (error) {
        console.error("Error parsing FastAPI WebSocket message:", error);
      }
    };
  }

  private scheduleReconnect() {
    // Never give up reconnecting for personal use - just slow down the attempts
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }

    // Cap at 30 seconds, but never stop trying
    const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), 30000);
    console.log(
      `Scheduling reconnect in ${delay / 1000}s (attempt ${this.reconnectAttempts + 1})`,
    );

    this.reconnectTimeout = setTimeout(() => {
      this.reconnectAttempts++;
      this.initializeConnection();
    }, delay);
  }

  private send(message: Record<string, unknown>) {
    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
      this.websocket.send(JSON.stringify(message));
    } else {
      console.warn("Cannot send message: WebSocket not connected");
    }
  }

  private emit(eventName: string, data: unknown) {
    const eventListeners = this.listeners.get(eventName);
    if (eventListeners) {
      eventListeners.forEach((listener) => {
        try {
          listener(data);
        } catch (error) {
          console.error(`Error in ${eventName} listener:`, error);
        }
      });
    }
  }

  /**
   * Add an event listener for job events
   */
  on<T extends keyof JobsWebSocketEvents>(
    event: T,
    listener: JobsWebSocketEvents[T],
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
  off<T extends keyof JobsWebSocketEvents>(
    event: T,
    listener: JobsWebSocketEvents[T],
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
   * Manually disconnect the WebSocket
   */
  disconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.websocket) {
      this.send({ type: "unsubscribe_from_jobs" });
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

  /**
   * Request an updated list of all jobs from the server
   */
  requestJobsList() {
    if (this.isConnectionActive()) {
      this.send({ type: "request_jobs_list" });
    } else {
      console.warn("Cannot request jobs list: WebSocket not connected");
    }
  }
}

// Create singleton instance
export const jobsWebSocketService = new JobsWebSocketService();

export default JobsWebSocketService;
