import { create } from "zustand";
import { sessionWebSocketService } from "../services/sessionWebSocketService";

interface ConnectedDevice {
  device_id: string;
  device_type: string;
  joined_at: string;
  is_self: boolean;
}

interface SessionInfo {
  session_id: string;
  display_code: string;
  is_host: boolean;
  device_type: string;
  device_count: number;
  connected_devices: ConnectedDevice[];
  created_at: string;
  expires_at: string;
  is_active: boolean;
}

interface SessionState {
  // Session data
  sessionId: string | null;
  displayCode: string | null;
  deviceId: string | null;  // Add device ID tracking
  isHost: boolean;
  deviceType: string;
  connectedDevices: ConnectedDevice[];
  sessionInfo: SessionInfo | null;

  // Connection state
  isConnected: boolean;
  isConnecting: boolean;
  connectionError: string | null;

  // Actions
  createSession: (deviceType?: string) => Promise<void>;
  joinSession: (codeOrId: string, deviceType?: string) => Promise<void>;
  leaveSession: () => Promise<void>;
  refreshSessionInfo: () => Promise<void>;
  clearSession: () => void;
}

export const useSessionStore = create<SessionState>((set, get) => ({
  // Initial state
  sessionId: null,
  displayCode: null,
  deviceId: null,
  isHost: false,
  deviceType: "performer",
  connectedDevices: [],
  sessionInfo: null,
  isConnected: false,
  isConnecting: false,
  connectionError: null,

  createSession: async (deviceType = "stage") => {
    set({ isConnecting: true, connectionError: null });

    try {
      const response = await fetch("/api/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ device_type: deviceType }),
      });

      if (!response.ok) {
        throw new Error(`Failed to create session: ${response.statusText}`);
      }

      const sessionData = await response.json();

      set({
        sessionId: sessionData.session_id,
        displayCode: sessionData.display_code,
        deviceId: sessionData.device_id,
        isHost: true,
        deviceType,
        isConnected: true,
        isConnecting: false,
        sessionInfo: sessionData,
      });

      // Update WebSocket services for new session
      sessionWebSocketService.connectToSession(sessionData.session_id);

      console.log("Session created:", sessionData);
    } catch (error) {
      console.error("Failed to create session:", error);
      set({
        connectionError: error instanceof Error ? error.message : "Failed to create session",
        isConnecting: false,
      });
    }
  },

  joinSession: async (codeOrId: string, deviceType = "performer") => {
    set({ isConnecting: true, connectionError: null });

    try {
      const endpoint = codeOrId.length === 4 ? "join-by-code" : "join-by-id";
      const response = await fetch(`/api/sessions/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          code: codeOrId.length === 4 ? codeOrId : undefined,
          session_id: codeOrId.length !== 4 ? codeOrId : undefined,
          device_type: deviceType,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to join session: ${response.statusText}`);
      }

      const sessionData = await response.json();

      set({
        sessionId: sessionData.session_id,
        displayCode: sessionData.display_code,
        deviceId: sessionData.device_id,
        isHost: sessionData.is_host,
        deviceType,
        isConnected: true,
        isConnecting: false,
        sessionInfo: sessionData,
      });

      // Update WebSocket services for new session
      sessionWebSocketService.connectToSession(sessionData.session_id);

      console.log("Joined session:", sessionData);
    } catch (error) {
      console.error("Failed to join session:", error);
      set({
        connectionError: error instanceof Error ? error.message : "Failed to join session",
        isConnecting: false,
      });
    }
  },

  leaveSession: async () => {
    const { sessionId } = get();
    if (!sessionId) return;

    try {
      const response = await fetch(`/api/sessions/${sessionId}/leave`, {
        method: "POST",
      });

      if (!response.ok) {
        console.warn("Failed to leave session on server:", response.statusText);
      }
    } catch (error) {
      console.warn("Error leaving session:", error);
    }

    // Clear local state regardless of server response
    get().clearSession();
  },

  refreshSessionInfo: async () => {
    const { sessionId } = get();
    if (!sessionId) return;

    try {
      const response = await fetch(`/api/sessions/${sessionId}/info`);
      if (!response.ok) {
        throw new Error(`Failed to get session info: ${response.statusText}`);
      }

      const sessionData = await response.json();
      set({ sessionInfo: sessionData });
    } catch (error) {
      console.error("Failed to refresh session info:", error);
    }
  },

  clearSession: () => {
    // Disconnect WebSocket services before clearing session
    sessionWebSocketService.disconnect();
    
    set({
      sessionId: null,
      displayCode: null,
      deviceId: null,
      isHost: false,
      deviceType: "performer",
      connectedDevices: [],
      sessionInfo: null,
      isConnected: false,
      isConnecting: false,
      connectionError: null,
    });
  },
}));