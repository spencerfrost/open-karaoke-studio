import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { sessionWebSocketService } from "../services/sessionWebSocketService";

interface ConnectedDevice {
  device_id: string;
  device_type: string;
  joined_at: string;
  is_self: boolean;
  display_name: string | null;  // Add display_name to connected devices
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
  deviceId: string | null;
  displayName: string | null;  // Add display name for the current user
  isHost: boolean;
  deviceType: string;
  connectedDevices: ConnectedDevice[];
  sessionInfo: SessionInfo | null;

  // Connection state
  isConnected: boolean;
  isConnecting: boolean;
  connectionError: string | null;

  // Recovery state
  isRecovering: boolean;
  recoveryError: string | null;

  // Actions
  createSession: (deviceType?: string, displayName?: string) => Promise<void>;
  joinSession: (codeOrId: string, deviceType?: string, displayName?: string) => Promise<void>;
  recoverHostSession: () => Promise<void>;
  recoverPerformerSession: () => Promise<void>;  // Add performer recovery method
  recoverSession: () => Promise<void>;  // Add general recovery method
  leaveSession: () => Promise<void>;
  refreshSessionInfo: () => Promise<void>;
  clearSession: () => void;
}

// Storage key for host sessions
const HOST_SESSION_STORAGE_KEY = "karaoke-host-session";
// Storage key for performer sessions
const PERFORMER_SESSION_STORAGE_KEY = "karaoke-performer-session";

export const useSessionStore = create<SessionState>()(
  persist(
    (set, get) => ({
      // Initial state
      sessionId: null,
      displayCode: null,
      deviceId: null,
      displayName: null,  // Initialize display name
      isHost: false,
      deviceType: "performer",
      connectedDevices: [],
      sessionInfo: null,
      isConnected: false,
      isConnecting: false,
      connectionError: null,
      isRecovering: false,
      recoveryError: null,

      createSession: async (deviceType = "stage", displayName) => {
        set({ isConnecting: true, connectionError: null });

        try {
          const response = await fetch("/api/sessions", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
              device_type: deviceType,
              display_name: displayName 
            }),
          });

          if (!response.ok) {
            throw new Error(`Failed to create session: ${response.statusText}`);
          }

          const sessionData = await response.json();

          set({
            sessionId: sessionData.session_id,
            displayCode: sessionData.display_code,
            deviceId: sessionData.device_id,
            displayName: displayName || null,  // Store the display name
            isHost: true,
            deviceType,
            isConnected: true,
            isConnecting: false,
            sessionInfo: sessionData,
            recoveryError: null, // Clear any recovery errors
          });

          // Update WebSocket services for new session - pass device_id for host registration
          sessionWebSocketService.connectToSession(sessionData.session_id, sessionData.device_id);

          // Setup session_ended event handler
          sessionWebSocketService.on('session_ended', (data) => {
            console.log('Session ended by host:', data?.reason);
            get().clearSession();
            // Show toast notification
            if (typeof window !== 'undefined' && window.location.pathname !== '/') {
              window.location.href = '/';
            }
          });

          console.log("Session created:", sessionData);
        } catch (error) {
          console.error("Failed to create session:", error);
          set({
            connectionError: error instanceof Error ? error.message : "Failed to create session",
            isConnecting: false,
          });
          throw error; // Re-throw to allow caller to handle
        }
      },

      joinSession: async (codeOrId: string, deviceType = "performer", displayName?: string) => {
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
              display_name: displayName,  // Send display name to backend
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
            displayName: displayName || null,  // Store the display name
            isHost: sessionData.is_host,
            deviceType,
            isConnected: true,
            isConnecting: false,
            sessionInfo: sessionData,
          });

          // Update WebSocket services for new session
          sessionWebSocketService.connectToSession(sessionData.session_id);

          // Setup session_ended event handler
          sessionWebSocketService.on('session_ended', (data) => {
            console.log('Session ended by host:', data?.reason);
            get().clearSession();
            // Show toast notification and redirect
            if (typeof window !== 'undefined' && window.location.pathname !== '/') {
              window.location.href = '/';
            }
          });

          // Store performer session data in localStorage if not a host
          if (!sessionData.is_host && displayName) {
            localStorage.setItem(PERFORMER_SESSION_STORAGE_KEY, JSON.stringify({
              sessionId: sessionData.session_id,
              deviceId: sessionData.device_id,
              displayName,
              timestamp: Date.now(),
            }));
          }

          console.log("Joined session:", sessionData);
        } catch (error) {
          console.error("Failed to join session:", error);
          set({
            connectionError: error instanceof Error ? error.message : "Failed to join session",
            isConnecting: false,
          });
          throw error;
        }
      },

      recoverHostSession: async () => {
        const storedSession = localStorage.getItem(HOST_SESSION_STORAGE_KEY);
        if (!storedSession) {
          return; // No stored session to recover
        }

        set({ isRecovering: true, recoveryError: null });

        try {
          const { sessionId, deviceId } = JSON.parse(storedSession);

          // Use new validation API endpoint from Phase 1
          const validationResponse = await fetch(`/api/sessions/${sessionId}/validate`);
          if (!validationResponse.ok) {
            if (validationResponse.status === 404 || validationResponse.status === 410) {
              // Session not found or expired - clear stored data
              localStorage.removeItem(HOST_SESSION_STORAGE_KEY);
              set({ isRecovering: false });
              return;
            }
            throw new Error(`Failed to validate session: ${validationResponse.statusText}`);
          }

          const validationData = await validationResponse.json();
          if (!validationData.valid) {
            // Session is invalid - clear stored data
            localStorage.removeItem(HOST_SESSION_STORAGE_KEY);
            set({ isRecovering: false });
            return;
          }

          // Get full session info
          const response = await fetch(`/api/sessions/${sessionId}/info`);
          if (!response.ok) {
            throw new Error(`Failed to get session info: ${response.statusText}`);
          }

          const sessionData = await response.json();

          // Verify we're still the host
          if (!sessionData.is_host) {
            localStorage.removeItem(HOST_SESSION_STORAGE_KEY);
            set({ isRecovering: false });
            return;
          }

          set({
            sessionId: sessionData.session_id,
            displayCode: sessionData.display_code,
            deviceId,
            isHost: true,
            deviceType: "stage",
            isConnected: true,
            isRecovering: false,
            sessionInfo: sessionData,
          });

          // Reconnect WebSocket - pass device_id for host registration
          sessionWebSocketService.connectToSession(sessionData.session_id, deviceId);

          // Setup session_ended event handler
          sessionWebSocketService.on('session_ended', (data) => {
            console.log('Session ended by host:', data?.reason);
            get().clearSession();
            // Show toast notification and redirect
            if (typeof window !== 'undefined' && window.location.pathname !== '/') {
              window.location.href = '/';
            }
          });

          console.log("Host session recovered:", sessionData);
        } catch (error) {
          console.error("Failed to recover host session:", error);
          set({
            recoveryError: error instanceof Error ? error.message : "Failed to recover session",
            isRecovering: false,
          });
          // Clear corrupted stored data
          localStorage.removeItem(HOST_SESSION_STORAGE_KEY);
        }
      },

      recoverSession: async () => {
        // Try to recover host session first
        await get().recoverHostSession();
        
        // If no host session was recovered, try performer session
        const state = get();
        if (!state.sessionId) {
          await get().recoverPerformerSession();
        }
      },

      recoverPerformerSession: async () => {
        const storedSession = localStorage.getItem(PERFORMER_SESSION_STORAGE_KEY);
        if (!storedSession) {
          return; // No stored session to recover
        }

        set({ isRecovering: true, recoveryError: null });

        try {
          const { sessionId, deviceId, displayName } = JSON.parse(storedSession);

          // Use new validation API endpoint from Phase 1
          const validationResponse = await fetch(`/api/sessions/${sessionId}/validate`);
          if (!validationResponse.ok) {
            if (validationResponse.status === 404 || validationResponse.status === 410) {
              // Session not found or expired - clear stored data
              localStorage.removeItem(PERFORMER_SESSION_STORAGE_KEY);
              set({ isRecovering: false });
              return;
            }
            throw new Error(`Failed to validate session: ${validationResponse.statusText}`);
          }

          const validationData = await validationResponse.json();
          if (!validationData.valid) {
            // Session is invalid - clear stored data
            localStorage.removeItem(PERFORMER_SESSION_STORAGE_KEY);
            set({ isRecovering: false });
            return;
          }

          // Get full session info
          const response = await fetch(`/api/sessions/${sessionId}/info`);
          if (!response.ok) {
            throw new Error(`Failed to get session info: ${response.statusText}`);
          }

          const sessionData = await response.json();

          set({
            sessionId: sessionData.session_id,
            displayCode: sessionData.display_code,
            deviceId,
            displayName,
            isHost: false,
            deviceType: "performer",
            isConnected: true,
            isRecovering: false,
            sessionInfo: sessionData,
          });

          // Reconnect WebSocket
          sessionWebSocketService.connectToSession(sessionData.session_id);

          // Setup session_ended event handler
          sessionWebSocketService.on('session_ended', (data) => {
            console.log('Session ended by host:', data?.reason);
            get().clearSession();
            // Show toast notification and redirect
            if (typeof window !== 'undefined' && window.location.pathname !== '/') {
              window.location.href = '/';
            }
          });

          console.log("Performer session recovered:", sessionData);
        } catch (error) {
          console.error("Failed to recover performer session:", error);
          set({
            recoveryError: error instanceof Error ? error.message : "Failed to recover session",
            isRecovering: false,
          });
          // Clear corrupted stored data
          localStorage.removeItem(PERFORMER_SESSION_STORAGE_KEY);
        }
      },

      leaveSession: async () => {
        const { sessionId, isHost } = get();
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

        // Clear stored session data for hosts and performers
        if (isHost) {
          localStorage.removeItem(HOST_SESSION_STORAGE_KEY);
        } else {
          localStorage.removeItem(PERFORMER_SESSION_STORAGE_KEY);
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
          displayName: null,  // Clear display name
          isHost: false,
          deviceType: "performer",
          connectedDevices: [],
          sessionInfo: null,
          isConnected: false,
          isConnecting: false,
          connectionError: null,
          isRecovering: false,
          recoveryError: null,
        });
      },
    }),
    {
      name: HOST_SESSION_STORAGE_KEY,
      storage: createJSONStorage(() => localStorage),
      // Only persist host session data
      partialize: (state) => ({
        sessionId: state.isHost ? state.sessionId : null,
        deviceId: state.isHost ? state.deviceId : null,
      }),
    }
  )
);