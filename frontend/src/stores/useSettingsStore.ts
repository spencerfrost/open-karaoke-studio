import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import {
  AppSettings,
  ThemeSettings,
  AudioSettings,
  ProcessingSettings,
  DisplaySettings,
} from "../types/Settings";

// Default settings
const defaultThemeSettings: ThemeSettings = {
  darkMode: true,
  themeName: "vintage",
};

const defaultAudioSettings: AudioSettings = {
  defaultVocalVolume: 50,
  defaultInstrumentalVolume: 100,
  fadeInDuration: 500,
  fadeOutDuration: 500,
};

const defaultProcessingSettings: ProcessingSettings = {
  quality: "medium",
  outputFormat: "mp3",
  autoProcessYouTube: true,
};

const defaultDisplaySettings: DisplaySettings = {
  lyricsSize: "medium",
  showAudioVisualizations: true,
  showProgress: true,
};

// Initial settings
const initialSettings: AppSettings = {
  theme: defaultThemeSettings,
  audio: defaultAudioSettings,
  processing: defaultProcessingSettings,
  display: defaultDisplaySettings,
};

// Define the store with actions
interface SettingsState extends AppSettings {
  // Actions
  setThemeSettings: (settings: Partial<ThemeSettings>) => void;
  setAudioSettings: (settings: Partial<AudioSettings>) => void;
  setProcessingSettings: (settings: Partial<ProcessingSettings>) => void;
  setDisplaySettings: (settings: Partial<DisplaySettings>) => void;
  resetSettings: () => void;
}

// Create the store using Zustand with persistence
export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      // Initial state
      ...initialSettings,
      
      // Actions
      setThemeSettings: (themeSettings) => 
        set((state) => ({ 
          theme: { ...state.theme, ...themeSettings }
        })),
        
      setAudioSettings: (audioSettings) => 
        set((state) => ({ 
          audio: { ...state.audio, ...audioSettings }
        })),
        
      setProcessingSettings: (processingSettings) => 
        set((state) => ({ 
          processing: { ...state.processing, ...processingSettings }
        })),
        
      setDisplaySettings: (displaySettings) => 
        set((state) => ({
          display: { ...state.display, ...displaySettings }
        })),
        
      resetSettings: () => set(initialSettings),
    }),
    {
      name: "openKaraokeSettings", // localStorage key
    }
  )
);