import { create } from "zustand";
import { persist } from "zustand/middleware";
import {
  AppSettings,
  ThemeSettings,
  AudioSettings,
  ProcessingSettings,
  DisplaySettings,
} from "@/types/Settings";
import { DEFAULT_THEME, isThemeName } from "@/lib/themes";

// Default settings
const defaultThemeSettings: ThemeSettings = {
  themeName: DEFAULT_THEME,
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
  songPreviewsEnabled: true,
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
          theme: { ...state.theme, ...themeSettings },
        })),

      setAudioSettings: (audioSettings) =>
        set((state) => ({
          audio: { ...state.audio, ...audioSettings },
        })),

      setProcessingSettings: (processingSettings) =>
        set((state) => ({
          processing: { ...state.processing, ...processingSettings },
        })),

      setDisplaySettings: (displaySettings) =>
        set((state) => ({
          display: { ...state.display, ...displaySettings },
        })),

      resetSettings: () => set(initialSettings),
    }),
    {
      name: "openKaraokeSettings", // localStorage key
      version: 2,
      migrate: (persisted, version) => {
        const state = persisted as Partial<AppSettings>;
        // v0 stored { darkMode, themeName: "vintage" | "synthwave" | "minimal" },
        // none of which were ever applied. v1's default was retro, and the
        // whole settings object is saved on any change, so a stored "retro" is
        // almost always the old default rather than a choice. Both become the
        // current default; a theme someone actually picked is kept.
        if (version < 2) {
          const themeName = state.theme?.themeName;
          state.theme = {
            themeName:
              isThemeName(themeName) && themeName !== "retro"
                ? themeName
                : DEFAULT_THEME,
          };
        }
        return state as SettingsState;
      },
    },
  ),
);
