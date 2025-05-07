/**
 * Performance Controls Store
 *
 * This store manages real-time performance controls across multiple devices during a karaoke performance.
 * It uses WebSockets to synchronize control changes like volume levels and lyrics size
 * between devices connected to the same global performance session.
 */
import { create } from "zustand";
import { io, Socket } from "socket.io-client";

// API base URL
const API_BASE_URL = "http://localhost:5000";

interface PerformanceControlsState {
  // Connection state
  connected: boolean;

  // Control values
  vocalVolume: number;
  instrumentalVolume: number;
  lyricsSize: "small" | "medium" | "large";

  // WebSocket instance
  socket: Socket | null;

  // Actions
  connect: () => void;
  disconnect: () => void;
  setVocalVolume: (volume: number) => void;
  setInstrumentalVolume: (volume: number) => void;
  setLyricsSize: (size: "small" | "medium" | "large") => void;
}

// Create socket.io instance for WebSocket communication
const createSocket = (): Socket => {
  return io(API_BASE_URL, {
    autoConnect: false,
    reconnection: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 1000,
  });
};

export const usePerformanceControlsStore = create<PerformanceControlsState>(
  (set, get) => ({
    // Initial state
    connected: false,
    vocalVolume: 50,
    instrumentalVolume: 100,
    lyricsSize: "medium",
    socket: null,

    // Connect to global performance controls
    connect: () => {
      // Create socket if it doesn't exist
      let socket = get().socket;
      if (!socket) {
        socket = createSocket();

        // Set up event listeners
        socket.on("connect", () => {
          console.log("Connected to performance control WebSocket");
          set({ connected: true });

          // Join the global performance controls
          socket?.emit("join_performance");
        });

        socket.on("disconnect", () => {
          console.log("Disconnected from performance control WebSocket");
          set({ connected: false });
        });

        socket.on("performance_state", (state) => {
          console.log("Received initial performance state", state);
          set({
            vocalVolume: state.vocal_volume,
            instrumentalVolume: state.instrumental_volume,
            lyricsSize: state.lyrics_size,
          });
        });

        socket.on("control_updated", (update) => {
          console.log("Control updated remotely:", update);
          // Map server control names to store properties
          if (update.control === "vocal_volume") {
            set({ vocalVolume: update.value });
          } else if (update.control === "instrumental_volume") {
            set({ instrumentalVolume: update.value });
          } else if (update.control === "lyrics_size") {
            set({ lyricsSize: update.value });
          }
        });

        // Store socket in state
        set({ socket });
      }

      // Connect if not already connected
      if (!socket.connected) {
        socket.connect();
      }
    },

    // Disconnect from performance controls
    disconnect: () => {
      const { socket } = get();
      if (socket && socket.connected) {
        socket.emit("leave_performance");
        socket.disconnect();
        set({ connected: false });
      }
    },

    // Update vocal volume locally and send to server
    setVocalVolume: (volume) => {
      const { socket } = get();
      set({ vocalVolume: volume });

      if (socket && socket.connected) {
        socket.emit("update_performance_control", {
          control: "vocal_volume",
          value: volume,
        });
      }
    },

    // Update instrumental volume locally and send to server
    setInstrumentalVolume: (volume) => {
      const { socket } = get();
      set({ instrumentalVolume: volume });

      if (socket && socket.connected) {
        socket.emit("update_performance_control", {
          control: "instrumental_volume",
          value: volume,
        });
      }
    },

    // Update lyrics size locally and send to server
    setLyricsSize: (size) => {
      const { socket } = get();
      set({ lyricsSize: size });

      if (socket && socket.connected) {
        socket.emit("update_performance_control", {
          control: "lyrics_size",
          value: size,
        });
      }
    },
  })
);
