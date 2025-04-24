import React, {
  createContext,
  useContext,
  useReducer,
  ReactNode,
  useEffect,
  useRef,
} from "react";
import { PlayerState, PlayerStatus, Lyric } from "../types/Player";
import { QueueItemWithSong } from "../types/Queue";
import { getAudioUrl } from "../services/songService";

// Action types
type PlayerAction =
  | { type: "SET_CURRENT_SONG"; payload: QueueItemWithSong | null }
  | { type: "SET_STATUS"; payload: PlayerStatus }
  | { type: "SET_CURRENT_TIME"; payload: number }
  | { type: "SET_DURATION"; payload: number }
  | { type: "SET_VOCAL_VOLUME"; payload: number }
  | { type: "SET_INSTRUMENTAL_VOLUME"; payload: number }
  | { type: "TOGGLE_PLAY_PAUSE" };

// Initial state
const initialState: PlayerState = {
  status: "idle",
  currentTime: 0,
  duration: 0,
  vocalVolume: 50,
  instrumentalVolume: 100,
  currentSong: null,
};

// Context
const PlayerContext = createContext<{
  state: PlayerState;
  dispatch: React.Dispatch<PlayerAction>;
  getCurrentLyric: () => { current: Lyric | null; next: Lyric | null };
}>({
  state: initialState,
  dispatch: () => null,
  getCurrentLyric: () => ({ current: null, next: null }),
});

// Reducer
const playerReducer = (
  state: PlayerState,
  action: PlayerAction,
): PlayerState => {
  switch (action.type) {
    case "SET_CURRENT_SONG":
      return {
        ...state,
        currentSong: action.payload,
        status: "idle",
        currentTime: 0,
      };
    case "SET_STATUS":
      return {
        ...state,
        status: action.payload,
      };
    case "TOGGLE_PLAY_PAUSE":
      return {
        ...state,
        status: state.status === "playing" ? "paused" : "playing",
      };
    case "SET_CURRENT_TIME":
      return {
        ...state,
        currentTime: action.payload,
      };
    case "SET_DURATION":
      return {
        ...state,
        duration: action.payload,
      };
    case "SET_VOCAL_VOLUME":
      return {
        ...state,
        vocalVolume: action.payload,
      };
    case "SET_INSTRUMENTAL_VOLUME":
      return {
        ...state,
        instrumentalVolume: action.payload,
      };
    default:
      return state;
  }
};

// Mock lyrics for development
const mockLyrics: { [key: string]: Lyric[] } = {};

// Provider component
export const PlayerProvider: React.FC<{ children: ReactNode }> = ({
  children,
}) => {
  const [state, dispatch] = useReducer(playerReducer, initialState);
  // Audio element refs for vocals and instrumental
  const vocalsAudioRef = useRef<HTMLAudioElement | null>(null);
  const instrumentalAudioRef = useRef<HTMLAudioElement | null>(null);

  // Function to get current and next lyrics based on the current time
  const getCurrentLyric = () => {
    if (!state.currentSong) {
      return { current: null, next: null };
    }

    const songId = state.currentSong.songId;
    const lyrics = mockLyrics[songId] || [];
    const now = state.currentTime;

    // Find the current lyric (the last one with time <= currentTime)
    const currentLyrics = lyrics.filter((lyric) => lyric.time <= now);
    const current =
      currentLyrics.length > 0
        ? currentLyrics.reduce(
            (latest, lyric) => (lyric.time > latest.time ? lyric : latest),
            { time: 0, text: "" },
          )
        : null;

    // Find the next lyric (the first one with time > currentTime)
    const nextLyricIndex = lyrics.findIndex((lyric) => lyric.time > now);
    const next = nextLyricIndex !== -1 ? lyrics[nextLyricIndex] : null;

    return { current, next };
  };

  // Load and prepare audio when song changes
  useEffect(() => {
    // Pause and clear previous audio
    vocalsAudioRef.current?.pause();
    instrumentalAudioRef.current?.pause();
    if (!state.currentSong) return;
    const songId = state.currentSong.songId;
    const vocals = new Audio(getAudioUrl(songId, "vocals"));
    const instrumental = new Audio(getAudioUrl(songId, "instrumental"));
    // Set initial volumes
    vocals.volume = state.vocalVolume / 100;
    instrumental.volume = state.instrumentalVolume / 100;
    // Sync events from vocals track
    vocals.addEventListener("loadedmetadata", () => {
      dispatch({ type: "SET_DURATION", payload: vocals.duration });
    });
    vocals.addEventListener("timeupdate", () => {
      dispatch({ type: "SET_CURRENT_TIME", payload: vocals.currentTime });
    });
    vocals.addEventListener("ended", () => {
      dispatch({ type: "SET_STATUS", payload: "idle" });
    });
    // Store refs
    vocalsAudioRef.current = vocals;
    instrumentalAudioRef.current = instrumental;
  }, [state.currentSong]);

  // Play or pause audio based on status
  useEffect(() => {
    const vocals = vocalsAudioRef.current;
    const instrumental = instrumentalAudioRef.current;
    if (!vocals || !instrumental) return;
    if (state.status === "playing") {
      vocals.play();
      instrumental.play();
    } else {
      vocals.pause();
      instrumental.pause();
    }
  }, [state.status]);

  // Update volumes when changed
  useEffect(() => {
    if (vocalsAudioRef.current) {
      vocalsAudioRef.current.volume = state.vocalVolume / 100;
    }
  }, [state.vocalVolume]);
  useEffect(() => {
    if (instrumentalAudioRef.current) {
      instrumentalAudioRef.current.volume = state.instrumentalVolume / 100;
    }
  }, [state.instrumentalVolume]);

  // Effect for updating player state based on playback status
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;

    if (state.status === "playing") {
      interval = setInterval(() => {
        dispatch({
          type: "SET_CURRENT_TIME",
          payload: state.currentTime + 0.1,
        });
      }, 100);
    }

    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [state.status, state.currentTime]);

  return (
    <PlayerContext.Provider value={{ state, dispatch, getCurrentLyric }}>
      {children}
    </PlayerContext.Provider>
  );
};

// Custom hook to use the player context
export const usePlayer = () => {
  const context = useContext(PlayerContext);
  if (context === undefined) {
    throw new Error("usePlayer must be used within a PlayerProvider");
  }
  return context;
};
