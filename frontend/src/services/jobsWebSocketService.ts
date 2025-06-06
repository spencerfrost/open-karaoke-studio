/**
 * WebSocket service for real-time job updates using Socket.IO
 */

import { io, Socket } from 'socket.io-client';

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
  private socket: Socket | null = null;
  private listeners: Map<string, Set<(data: unknown) => void>> = new Map();
  private isConnected = false;
  private maxReconnectAttempts = 5;

  constructor() {
    this.initializeConnection();
  }

  private initializeConnection() {
    try {
      // Get the base URL for WebSocket connection
      const host = window.location.host;
      const socketUrl = process.env.NODE_ENV === 'development' 
        ? 'http://localhost:5000' 
        : `${window.location.protocol}//${host}`;

      this.socket = io(`${socketUrl}/jobs`, {
        transports: ['websocket', 'polling'],
        autoConnect: true,
        reconnection: true,
        reconnectionAttempts: this.maxReconnectAttempts,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
      });

      this.setupEventHandlers();
    } catch (error) {
      console.error('Failed to initialize WebSocket connection:', error);
    }
  }

  private setupEventHandlers() {
    if (!this.socket) return;

    this.socket.on('connect', () => {
      console.log('Connected to jobs WebSocket');
      this.isConnected = true;
      
      // Subscribe to job updates
      this.socket?.emit('subscribe_to_jobs');
    });

    this.socket.on('disconnect', () => {
      console.log('Disconnected from jobs WebSocket');
      this.isConnected = false;
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      this.isConnected = false;
    });

    this.socket.on('subscribed', (data) => {
      console.log('Subscribed to job updates:', data);
    });

    // Set up job event listeners
    this.socket.on('job_created', (data: JobData) => {
      this.emit('job_created', data);
    });

    this.socket.on('job_updated', (data: JobData) => {
      this.emit('job_updated', data);
    });

    this.socket.on('job_completed', (data: JobData) => {
      this.emit('job_completed', data);
    });

    this.socket.on('job_failed', (data: JobData) => {
      this.emit('job_failed', data);
    });

    this.socket.on('job_cancelled', (data: JobData) => {
      this.emit('job_cancelled', data);
    });

    this.socket.on('jobs_list', (data: { jobs: JobData[] }) => {
      this.emit('jobs_list', data);
    });
  }

  private emit(eventName: string, data: unknown) {
    const eventListeners = this.listeners.get(eventName);
    if (eventListeners) {
      eventListeners.forEach(listener => {
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
    listener: JobsWebSocketEvents[T]
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
    listener: JobsWebSocketEvents[T]
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
    return this.isConnected && this.socket?.connected === true;
  }

  /**
   * Manually disconnect the WebSocket
   */
  disconnect() {
    if (this.socket) {
      this.socket.emit('unsubscribe_from_jobs');
      this.socket.disconnect();
      this.socket = null;
    }
    this.isConnected = false;
    this.listeners.clear();
  }

  /**
   * Manually reconnect the WebSocket
   */
  reconnect() {
    if (this.socket) {
      this.socket.connect();
    } else {
      this.initializeConnection();
    }
  }

  /**
   * Request an updated list of all jobs from the server
   */
  requestJobsList() {
    if (this.socket && this.isConnected) {
      this.socket.emit('request_jobs_list');
    } else {
      console.warn('Cannot request jobs list: WebSocket not connected');
    }
  }
}

// Create singleton instance
export const jobsWebSocketService = new JobsWebSocketService();

export default JobsWebSocketService;
