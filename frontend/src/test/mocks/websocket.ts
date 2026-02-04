import { vi } from "vitest";

/**
 * Mock performance state for testing
 */
export const mockPerformanceState = {
  vocal_volume: 0,
  instrumental_volume: 1.0,
  lyrics_size: "medium" as const,
  lyrics_offset: 0,
  current_time: 0,
  duration: 180,
  is_playing: false,
  current_song_id: null,
  is_ready: false,
};

/**
 * Mock session WebSocket service
 * Tracks listeners and provides helpers to simulate WebSocket events
 */
export function createMockSessionWebSocketService() {
  const listeners = new Map<string, Set<(data: unknown) => void>>();

  const mockService = {
    // Connection state
    isConnected: false,
    currentSessionId: null as string | null,
    deviceId: null as string | null,

    // Mock implementations
    connectToSession: vi.fn((sessionId: string, _hostDeviceId?: string) => {
      mockService.isConnected = true;
      mockService.currentSessionId = sessionId;
      mockService.deviceId = `mock-device-${Date.now()}`;

      // Simulate immediate connection
      setTimeout(() => {
        mockService.emit("session_connected", {
          session_id: sessionId,
          device_id: mockService.deviceId,
          is_host: !!_hostDeviceId,
          performance_state: { ...mockPerformanceState },
        });
      }, 0);
    }),

    disconnect: vi.fn(() => {
      mockService.isConnected = false;
      mockService.currentSessionId = null;
      mockService.deviceId = null;
      listeners.clear();
    }),

    reconnect: vi.fn(() => {
      if (mockService.currentSessionId) {
        mockService.connectToSession(mockService.currentSessionId);
      }
    }),

    isConnectionActive: vi.fn(() => mockService.isConnected),
    getDeviceId: vi.fn(() => mockService.deviceId),

    // Event subscription
    on: vi.fn((event: string, listener: (data: unknown) => void) => {
      if (!listeners.has(event)) {
        listeners.set(event, new Set());
      }
      listeners.get(event)!.add(listener);

      // Return cleanup function
      return () => {
        mockService.off(event, listener);
      };
    }),

    off: vi.fn((event: string, listener: (data: unknown) => void) => {
      const eventListeners = listeners.get(event);
      if (eventListeners) {
        eventListeners.delete(listener);
        if (eventListeners.size === 0) {
          listeners.delete(event);
        }
      }
    }),

    // Performance control methods
    updatePerformanceControl: vi.fn((_control: string, _value: unknown) => {
      // Mock - can verify calls in tests
    }),

    updatePlayerState: vi.fn(
      (_state: {
        isPlaying?: boolean;
        currentTime?: number;
        duration?: number;
      }) => {
        // Mock - can verify calls in tests
      },
    ),

    playback: vi.fn(),
    pause: vi.fn(),
    songLoaded: vi.fn((_songId: string, _duration: number) => {}),
    songReady: vi.fn((_songId: string, _duration: number) => {}),

    // Queue methods
    requestQueueUpdate: vi.fn(),
    notifyQueueChanged: vi.fn(),

    // Test helper: emit an event to all listeners
    emit: (eventName: string, data: unknown) => {
      const eventListeners = listeners.get(eventName);
      if (eventListeners) {
        eventListeners.forEach((listener) => {
          listener(data);
        });
      }
    },

    // Test helper: get all listeners for an event
    getListeners: (eventName: string) => {
      return listeners.get(eventName) || new Set();
    },

    // Test helper: clear all listeners
    clearListeners: () => {
      listeners.clear();
    },

    // Test helper: reset mock
    reset: () => {
      mockService.isConnected = false;
      mockService.currentSessionId = null;
      mockService.deviceId = null;
      listeners.clear();
      vi.clearAllMocks();
    },
  };

  return mockService;
}

/**
 * Mock jobs WebSocket service
 */
export function createMockJobsWebSocketService() {
  const listeners = new Map<string, Set<(data: unknown) => void>>();

  const mockService = {
    isConnected: false,

    connect: vi.fn(() => {
      mockService.isConnected = true;
    }),

    disconnect: vi.fn(() => {
      mockService.isConnected = false;
      listeners.clear();
    }),

    on: vi.fn((event: string, listener: (data: unknown) => void) => {
      if (!listeners.has(event)) {
        listeners.set(event, new Set());
      }
      listeners.get(event)!.add(listener);
      return () => mockService.off(event, listener);
    }),

    off: vi.fn((event: string, listener: (data: unknown) => void) => {
      listeners.get(event)?.delete(listener);
    }),

    // Test helper
    emit: (eventName: string, data: unknown) => {
      listeners.get(eventName)?.forEach((listener) => listener(data));
    },

    reset: () => {
      mockService.isConnected = false;
      listeners.clear();
      vi.clearAllMocks();
    },
  };

  return mockService;
}

// Pre-created mock instances for easy import
export const mockSessionWebSocketService = createMockSessionWebSocketService();
export const mockJobsWebSocketService = createMockJobsWebSocketService();
