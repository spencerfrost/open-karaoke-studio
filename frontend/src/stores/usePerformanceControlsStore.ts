/**
 * Performance Controls Store
 *
 * This store manages real-time performance controls across multiple devices during a karaoke performance.
 * It uses WebSockets to synchronize control changes like volume levels and lyrics size
 * between devices connected to the same global performance session.
 */
import { create } from "zustand";
import { io, Socket } from "socket.io-client";

const BASE_URL = import.meta.env.VITE_BACKEND_URL ?? "http://localhost:5000";

interface PerformanceControlsState {
  // Connection state
  connected: boolean;

  // Control values
  vocalVolume: number; // 0.0–1.0
  instrumentalVolume: number; // 0.0–1.0
  lyricsSize: "small" | "medium" | "large";
  isPlaying: boolean;

  playerState: {
    isPlaying: boolean;
    currentTime: number;
    duration: number;
  } | null;

  // WebSocket instance
  socket: Socket | null;

  // Actions
  connect: () => void;
  disconnect: () => void;
  setVocalVolume: (volume: number) => void; // expects 0.0–1.0
  setInstrumentalVolume: (volume: number) => void; // expects 0.0–1.0
  setLyricsSize: (size: "small" | "medium" | "large") => void;

  // Playback control actions
  togglePlayback: () => void;
  sendPause: () => void;
  sendSeek: (time: number) => void;
  sendSetSong: (songId: string) => void;
  // Playback event listeners (for player to subscribe)
  onPlay: (cb: () => void) => void;
  onPause: (cb: () => void) => void;
  onSeek: (cb: (time: number) => void) => void;
  onSetSong: (cb: (songId: string) => void) => void;
}

// Create socket.io instance for WebSocket communication
const createSocket = (): Socket => {
  return io(BASE_URL, {
    autoConnect: false,
    reconnection: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 1000,
  });
};

export const usePerformanceControlsStore = create<PerformanceControlsState>(
  (set, get) => {
    // Internal event listeners
    const playListeners: Array<() => void> = [];
    const pauseListeners: Array<() => void> = [];
    const seekListeners: Array<(time: number) => void> = [];
    const setSongListeners: Array<(songId: string) => void> = [];

    return {
      // Initial state
      connected: false,
      vocalVolume: 0,
      instrumentalVolume: 1.0,
      lyricsSize: "medium",
      isPlaying: false,
      playerState: null,
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
          socket.on("disconnect", () => set({ connected: false }));

          // Listen for player state updates
          socket.on("player_state", (data) => {
            set({ playerState: data });
          });

          socket.on("performance_state", (state) => {
            console.log("Received initial performance state", state);
            set({
              vocalVolume: state.vocal_volume,
              instrumentalVolume: state.instrumental_volume,
              lyricsSize: state.lyrics_size,
              isPlaying: state.is_playing,
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

          socket.on("player_state_updated", (data) => {
            console.log("Received player state update", data);
            set({ playerState: data });
          });

          // Playback event listeners
          socket.on("toggle_playback", () => {
            console.log("Recieved toggle_playback event");
            if (get().isPlaying) {
              set({ isPlaying: false });
              pauseListeners.forEach((cb) => cb());
            } else {
              set({ isPlaying: true });
              playListeners.forEach((cb) => cb());
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
        if (socket?.connected) {
          socket.disconnect();
        }
        set({ connected: false });
      },

      // Update vocal volume locally and send to server
      setVocalVolume: (volume) => {
        const { socket } = get();
        // Clamp to 0.0–1.0
        const normalized = Math.max(0, Math.min(1, volume));
        set({ vocalVolume: normalized });

        if (socket?.connected) {
          socket.emit("update_performance_control", {
            control: "vocal_volume",
            value: normalized,
          });
        }
      },

      // Update instrumental volume locally and send to server
      setInstrumentalVolume: (volume) => {
        const { socket } = get();
        const normalized = Math.max(0, Math.min(1, volume));
        set({ instrumentalVolume: normalized });

        if (socket?.connected) {
          socket.emit("update_performance_control", {
            control: "instrumental_volume",
            value: normalized,
          });
        }
      },

      // Update lyrics size locally and send to server
      setLyricsSize: (size) => {
        const { socket } = get();
        set({ lyricsSize: size });

        if (socket?.connected) {
          socket.emit("update_performance_control", {
            control: "lyrics_size",
            value: size,
          });
        }
      },

      // Playback control actions
      togglePlayback: () => {
        const { socket } = get();
        if (socket?.connected) {
          console.log("togglePlayback");
          socket.emit("toggle_playback");
        }
      },
      sendPause: () => {
        const { socket } = get();
        if (socket?.connected) {
          socket.emit("playback_pause");
        }
      },
      sendSeek: (time) => {
        const { socket } = get();
        if (socket?.connected) {
          socket.emit("playback_seek", { time });
        }
      },
      sendSetSong: (songId) => {
        const { socket } = get();
        if (socket?.connected) {
          socket.emit("playback_set_song", { song_id: songId });
        }
      },
      onPlay: (cb) => {
        playListeners.push(cb);
      },
      onPause: (cb) => {
        pauseListeners.push(cb);
      },
      onSeek: (cb) => {
        seekListeners.push(cb);
      },
      onSetSong: (cb) => {
        setSongListeners.push(cb);
      },
    };
  }
);
