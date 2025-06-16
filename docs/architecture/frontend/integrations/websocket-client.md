# WebSocket Client Architecture

## Overview

The WebSocket client architecture provides real-time communication capabilities for the Open Karaoke Studio frontend. It manages multiple WebSocket connections for different features including job processing updates, performance controls synchronization, and queue management.

## Current Implementation Status

**Primary Files**:
- `frontend/src/services/jobsWebSocketService.ts` - Job processing updates service
- `frontend/src/hooks/useJobsWebSocket.ts` - React hooks for job status updates
- `frontend/src/stores/useKaraokePlayerStore.ts` - Performance controls WebSocket integration
- `frontend/src/hooks/useWebSocket.ts` - Generic WebSocket connection hook

**Status**: ✅ Complete with production-ready implementation  
**Integration**: Fully integrated with backend WebSocket endpoints

## Core Responsibilities

### Real-time Job Processing Updates
- **Processing Status**: Live updates for song upload and processing workflows
- **Progress Tracking**: Real-time progress updates for long-running audio processing tasks
- **Error Notifications**: Immediate notification of processing failures
- **Queue Management**: Live updates of the processing queue state

### Performance Controls Synchronization
- **Multi-device Control**: Synchronized controls across multiple devices for live performances
- **Player State Sync**: Real-time synchronization of playback state, volume, and settings
- **Karaoke Features**: Live control of vocal/instrumental volume and lyrics display
- **Remote Control**: Mobile device control of main performance system

### Connection Management
- **Automatic Reconnection**: Intelligent reconnection with exponential backoff
- **Connection Health Monitoring**: Real-time connection status tracking
- **Error Recovery**: Graceful handling of network interruptions
- **Multiple Connection Support**: Simultaneous connections to different WebSocket namespaces

## Implementation Details

### Jobs WebSocket Service

```typescript
// Singleton service for job processing updates
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
      // Environment-specific connection setup
      let socketUrl: string;
      
      if (import.meta.env.DEV) {
        // Development: use Vite proxy
        socketUrl = `${window.location.protocol}//${window.location.host}`;
      } else {
        // Production: direct backend connection
        const backendUrl = import.meta.env.VITE_BACKEND_URL || 
                          `${window.location.protocol}//${window.location.host}`;
        socketUrl = backendUrl;
      }

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

    // Connection lifecycle
    this.socket.on('connect', () => {
      console.log('Connected to jobs WebSocket');
      this.isConnected = true;
      this.socket?.emit('subscribe_to_jobs');
    });

    this.socket.on('disconnect', () => {
      console.log('Disconnected from jobs WebSocket');
      this.isConnected = false;
    });

    // Job event handlers
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
  }

  // Event listener management
  on<T extends keyof JobsWebSocketEvents>(
    event: T,
    listener: JobsWebSocketEvents[T]
  ) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(listener as (data: unknown) => void);

    // Return cleanup function
    return () => {
      this.off(event, listener);
    };
  }

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
}

// Singleton instance
export const jobsWebSocketService = new JobsWebSocketService();
```

### React Hook Integration

```typescript
// Hook for managing real-time job updates
export function useJobsWebSocket() {
  const [jobs, setJobs] = useState<SongProcessingStatus[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  // Update job in the list
  const updateJob = useCallback((jobData: JobData) => {
    const processedJob = mapJobToProcessingStatus(jobData);
    
    setJobs(prevJobs => {
      const existingIndex = prevJobs.findIndex(j => j.id === jobData.id);
      
      if (existingIndex >= 0) {
        // Update existing job
        const updatedJobs = [...prevJobs];
        updatedJobs[existingIndex] = processedJob;
        
        // Remove completed/failed jobs after delay
        if (processedJob.status === 'processed' || processedJob.status === 'error') {
          setTimeout(() => {
            setJobs(current => current.filter(j => j.id !== jobData.id));
          }, 3000);
        }
        
        return updatedJobs;
      } else {
        // Add new job if processing
        if (['queued', 'processing'].includes(processedJob.status)) {
          return [...prevJobs, processedJob];
        }
        return prevJobs;
      }
    });

    // Invalidate React Query caches
    queryClient.invalidateQueries({ queryKey: ['processing-queue'] });
    queryClient.invalidateQueries({ queryKey: ['processing-status', jobData.id] });
  }, [queryClient]);

  // Set up WebSocket event listeners
  useEffect(() => {
    const cleanupFunctions: (() => void)[] = [];

    try {
      cleanupFunctions.push(
        jobsWebSocketService.on('job_created', updateJob),
        jobsWebSocketService.on('job_updated', updateJob),
        jobsWebSocketService.on('job_completed', updateJob),
        jobsWebSocketService.on('job_failed', updateJob),
        jobsWebSocketService.on('job_cancelled', (jobData) => {
          setTimeout(() => removeJob(jobData.id), 1000);
        }),
        jobsWebSocketService.on('jobs_list', handleJobsList)
      );

      // Connection status monitoring
      const checkConnection = () => {
        setIsConnected(jobsWebSocketService.isConnectionActive());
      };

      const connectionCheck = setInterval(checkConnection, 1000);
      checkConnection();

      cleanupFunctions.push(() => clearInterval(connectionCheck));

      return () => {
        cleanupFunctions.forEach(cleanup => cleanup());
      };
    } catch (err) {
      setError(err instanceof Error ? err.message : 'WebSocket connection failed');
      return () => {
        cleanupFunctions.forEach(cleanup => cleanup());
      };
    }
  }, [updateJob, removeJob, handleJobsList]);

  return {
    jobs,
    isConnected,
    error,
    refetch: useCallback(() => {
      if (jobsWebSocketService.isConnectionActive()) {
        jobsWebSocketService.requestJobsList();
        setError(null);
      } else {
        jobsWebSocketService.reconnect();
        setError('WebSocket disconnected. Attempting to reconnect...');
      }
    }, []),
  };
}
```

### Performance Controls WebSocket Integration

```typescript
// Karaoke player store with WebSocket integration
export const useKaraokePlayerStore = create<KaraokePlayerState>((set, get) => ({
  // WebSocket connection state
  socket: null,
  connected: false,
  
  // Performance control state
  vocalVolume: 0,
  instrumentalVolume: 1,
  lyricsSize: 'medium',
  lyricsOffset: 0,
  isPlaying: false,
  
  // WebSocket connection management
  connect: () => {
    const socket = createSocket();
    
    socket.on('connect', () => {
      set({ connected: true });
      socket.emit('join_performance');
    });
    
    socket.on('disconnect', () => {
      set({ connected: false });
    });
    
    // Performance state synchronization
    socket.on('performance_state', (state: PerformanceState) => {
      set({
        vocalVolume: state.vocal_volume,
        instrumentalVolume: state.instrumental_volume,
        lyricsSize: state.lyrics_size,
        lyricsOffset: state.lyrics_offset,
        isPlaying: state.is_playing,
      });
    });
    
    // Playback control events
    socket.on('playback_play', () => {
      const { play } = get();
      play();
    });
    
    socket.on('playback_pause', () => {
      const { pause } = get();
      pause();
    });
    
    socket.connect();
    set({ socket });
  },
  
  disconnect: () => {
    const { socket } = get();
    if (socket) {
      socket.emit('leave_performance');
      socket.disconnect();
      set({ socket: null, connected: false });
    }
  },
  
  // Performance control actions with WebSocket sync
  setVocalVolume: (volume: number) => {
    set({ vocalVolume: volume });
    socketEmit('update_performance_control', {
      vocal_volume: volume
    });
  },
  
  setInstrumentalVolume: (volume: number) => {
    set({ instrumentalVolume: volume });
    socketEmit('update_performance_control', {
      instrumental_volume: volume
    });
  },
  
  // Player control actions
  play: () => {
    set({ isPlaying: true });
    socketEmit('playback_play', {});
  },
  
  pause: () => {
    set({ isPlaying: false });
    socketEmit('playback_pause', {});
  },
}));

// Helper function for socket emission
function socketEmit(event: string, data: unknown) {
  const { socket } = useKaraokePlayerStore.getState();
  if (socket?.connected) {
    socket.emit(event, data);
  }
}
```

### Generic WebSocket Hook

```typescript
// Reusable WebSocket connection hook
export function useWebSocketConnection(url: string, options: {
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Error) => void;
  namespace?: string;
} = {}) {
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const socketRef = useRef<Socket | null>(null);
  
  const connect = useCallback(() => {
    if (socketRef.current?.connected) return;
    
    const fullUrl = options.namespace ? `${url}/${options.namespace}` : url;
    socketRef.current = io(fullUrl, {
      autoConnect: true,
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });
    
    socketRef.current.on('connect', () => {
      setConnected(true);
      setError(null);
      options.onConnect?.();
    });
    
    socketRef.current.on('disconnect', () => {
      setConnected(false);
      options.onDisconnect?.();
    });
    
    socketRef.current.on('connect_error', (err) => {
      setError(err);
      options.onError?.(err);
    });
  }, [url, options]);
  
  const disconnect = useCallback(() => {
    socketRef.current?.disconnect();
    socketRef.current = null;
    setConnected(false);
  }, []);
  
  useEffect(() => {
    connect();
    return disconnect;
  }, [connect, disconnect]);
  
  return {
    socket: socketRef.current,
    connected,
    error,
    connect,
    disconnect,
  };
}
```

## Integration Points

### React Query Synchronization
- **Cache Invalidation**: WebSocket events trigger React Query cache updates
- **Optimistic Updates**: WebSocket events provide real-time validation of optimistic updates
- **Background Sync**: Automatic cache refresh when WebSocket reconnects
- **Conflict Resolution**: WebSocket events override stale cached data

### Zustand Store Integration
- **State Synchronization**: WebSocket events update global application state
- **Action Broadcasting**: Local actions broadcast to other connected clients
- **State Persistence**: Critical state persisted across WebSocket disconnections
- **Multi-device Sync**: State changes synchronized across multiple devices

### Component Integration
- **Real-time UI Updates**: Components automatically re-render on WebSocket state changes
- **Loading States**: Connection status displayed throughout the interface
- **Error Handling**: WebSocket errors displayed with user-friendly messages
- **Offline Handling**: Graceful degradation when WebSocket unavailable

## Design Patterns

### Event-Driven Architecture
```typescript
// Centralized event handling pattern
interface WebSocketEventMap {
  'job_created': (job: JobData) => void;
  'job_updated': (job: JobData) => void;
  'job_completed': (job: JobData) => void;
  'performance_state': (state: PerformanceState) => void;
  'playback_control': (action: PlaybackAction) => void;
}

class WebSocketEventManager {
  private handlers = new Map<string, Set<Function>>();
  
  on<K extends keyof WebSocketEventMap>(
    event: K, 
    handler: WebSocketEventMap[K]
  ) {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, new Set());
    }
    this.handlers.get(event)!.add(handler);
    
    return () => this.off(event, handler);
  }
  
  emit<K extends keyof WebSocketEventMap>(
    event: K,
    data: Parameters<WebSocketEventMap[K]>[0]
  ) {
    const eventHandlers = this.handlers.get(event);
    if (eventHandlers) {
      eventHandlers.forEach(handler => {
        try {
          handler(data);
        } catch (error) {
          console.error(`Error in ${event} handler:`, error);
        }
      });
    }
  }
}
```

### Connection Pooling Pattern
```typescript
// Efficient connection management
class WebSocketConnectionPool {
  private connections = new Map<string, Socket>();
  
  getConnection(namespace: string): Socket {
    if (this.connections.has(namespace)) {
      return this.connections.get(namespace)!;
    }
    
    const socket = io(`${BASE_URL}/${namespace}`, {
      autoConnect: true,
      reconnection: true,
    });
    
    this.connections.set(namespace, socket);
    return socket;
  }
  
  closeConnection(namespace: string) {
    const socket = this.connections.get(namespace);
    if (socket) {
      socket.disconnect();
      this.connections.delete(namespace);
    }
  }
  
  closeAllConnections() {
    this.connections.forEach(socket => socket.disconnect());
    this.connections.clear();
  }
}
```

### Retry Strategy Pattern
```typescript
// Intelligent reconnection strategy
class WebSocketRetryStrategy {
  private retryCount = 0;
  private maxRetries = 5;
  private baseDelay = 1000;
  private maxDelay = 30000;
  
  async retry<T>(operation: () => Promise<T>): Promise<T> {
    try {
      const result = await operation();
      this.retryCount = 0; // Reset on success
      return result;
    } catch (error) {
      if (this.retryCount >= this.maxRetries) {
        throw new Error(`Max retries (${this.maxRetries}) exceeded`);
      }
      
      const delay = Math.min(
        this.baseDelay * Math.pow(2, this.retryCount),
        this.maxDelay
      );
      
      this.retryCount++;
      
      await new Promise(resolve => setTimeout(resolve, delay));
      return this.retry(operation);
    }
  }
}
```

## Performance Considerations

### Connection Optimization
- **Connection Pooling**: Reuse connections across components to minimize overhead
- **Namespace Separation**: Separate connections for different feature sets
- **Lazy Connection**: Connect only when components need real-time updates
- **Auto-cleanup**: Automatic disconnection when components unmount

### Data Transfer Efficiency
- **Event Filtering**: Subscribe only to relevant events to reduce data transfer
- **Data Compression**: Use WebSocket compression for large payloads
- **Batching**: Batch multiple updates to reduce event frequency
- **Delta Updates**: Send only changed data rather than full state

### Memory Management
- **Event Cleanup**: Automatic removal of event listeners on component unmount
- **Connection Cleanup**: Proper disposal of WebSocket connections
- **State Cleanup**: Clear related state when WebSocket disconnects
- **Memory Monitoring**: Track memory usage of WebSocket buffers

## Error Handling

### Connection Error Recovery
```typescript
const handleConnectionError = (error: Error, namespace: string) => {
  console.error(`WebSocket connection error for ${namespace}:`, error);
  
  // Determine error type and appropriate response
  if (error.message.includes('Network')) {
    // Network error - attempt reconnection
    scheduleReconnection(namespace);
  } else if (error.message.includes('Unauthorized')) {
    // Auth error - redirect to login
    handleAuthError();
  } else {
    // Unknown error - show user notification
    showErrorNotification('Connection failed. Please try again.');
  }
};
```

### Data Validation
```typescript
// Validate incoming WebSocket data
const validateJobData = (data: unknown): data is JobData => {
  return (
    typeof data === 'object' &&
    data !== null &&
    'id' in data &&
    'status' in data &&
    typeof (data as any).id === 'string' &&
    typeof (data as any).status === 'string'
  );
};

// Use validation in event handlers
socket.on('job_updated', (data) => {
  if (validateJobData(data)) {
    updateJob(data);
  } else {
    console.error('Invalid job data received:', data);
  }
});
```

### Graceful Degradation
```typescript
// Fallback to HTTP polling when WebSocket unavailable
export const useJobStatusFallback = (jobId: string) => {
  const { isConnected } = useJobsWebSocket();
  
  // HTTP polling fallback
  const { data: jobStatus } = useQuery({
    queryKey: ['job-status', jobId],
    queryFn: () => fetchJobStatus(jobId),
    enabled: !isConnected && !!jobId,
    refetchInterval: isConnected ? false : 2000, // Poll every 2 seconds
  });
  
  return jobStatus;
};
```

## Security Considerations

### Authentication Integration
- **Token Validation**: Automatic JWT token validation on WebSocket connections
- **Session Management**: Proper handling of authentication state changes
- **Authorization**: Namespace-level authorization for different user roles
- **Secure Transport**: WSS (WebSocket Secure) in production environments

### Data Privacy
- **Event Filtering**: Users receive only events they're authorized to see
- **Data Sanitization**: Sanitize all outgoing and incoming WebSocket data
- **Rate Limiting**: Client-side rate limiting to prevent abuse
- **Connection Limits**: Prevent excessive connection attempts

## Future Enhancements

### Advanced Features
- **Message Queuing**: Queue messages during disconnection for replay on reconnect
- **Event History**: Store critical events for replay and debugging
- **Conflict Resolution**: Advanced conflict resolution for concurrent updates
- **Load Balancing**: Support for multiple WebSocket servers with load balancing

### Performance Improvements
- **Binary Protocols**: Use binary protocols for high-frequency updates
- **Edge Caching**: Cache WebSocket messages at CDN edge locations
- **Compression**: Advanced compression algorithms for large data transfers
- **Connection Sharing**: Share connections across browser tabs

---

**Real-time Benefits**: This WebSocket architecture enables immediate user feedback, synchronized multi-device experiences, and seamless collaboration features that are essential for the karaoke application's live performance requirements.
