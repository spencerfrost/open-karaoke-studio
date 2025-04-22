import React, { createContext, useContext, useReducer, ReactNode, useEffect } from 'react';
import {
  AppSettings,
  ThemeSettings,
  AudioSettings,
  ProcessingSettings,
  DisplaySettings
} from '../types/Settings';

// Default settings
const defaultThemeSettings: ThemeSettings = {
  darkMode: true,
  themeName: 'vintage'
};

const defaultAudioSettings: AudioSettings = {
  defaultVocalVolume: 50,
  defaultInstrumentalVolume: 100,
  fadeInDuration: 500,
  fadeOutDuration: 500
};

const defaultProcessingSettings: ProcessingSettings = {
  quality: 'medium',
  outputFormat: 'mp3',
  autoProcessYouTube: true
};

const defaultDisplaySettings: DisplaySettings = {
  lyricsSize: 'medium',
  showAudioVisualizations: true,
  showProgress: true
};

// Initial state
const initialSettings: AppSettings = {
  theme: defaultThemeSettings,
  audio: defaultAudioSettings,
  processing: defaultProcessingSettings,
  display: defaultDisplaySettings
};

// Action types
type SettingsAction =
  | { type: 'SET_THEME_SETTINGS'; payload: Partial<ThemeSettings> }
  | { type: 'SET_AUDIO_SETTINGS'; payload: Partial<AudioSettings> }
  | { type: 'SET_PROCESSING_SETTINGS'; payload: Partial<ProcessingSettings> }
  | { type: 'SET_DISPLAY_SETTINGS'; payload: Partial<DisplaySettings> }
  | { type: 'RESET_SETTINGS' };

// Context
const SettingsContext = createContext<{
  settings: AppSettings;
  dispatch: React.Dispatch<SettingsAction>;
}>({
  settings: initialSettings,
  dispatch: () => null
});

// Reducer
const settingsReducer = (state: AppSettings, action: SettingsAction): AppSettings => {
  switch (action.type) {
    case 'SET_THEME_SETTINGS':
      return {
        ...state,
        theme: {
          ...state.theme,
          ...action.payload
        }
      };
    case 'SET_AUDIO_SETTINGS':
      return {
        ...state,
        audio: {
          ...state.audio,
          ...action.payload
        }
      };
    case 'SET_PROCESSING_SETTINGS':
      return {
        ...state,
        processing: {
          ...state.processing,
          ...action.payload
        }
      };
    case 'SET_DISPLAY_SETTINGS':
      return {
        ...state,
        display: {
          ...state.display,
          ...action.payload
        }
      };
    case 'RESET_SETTINGS':
      return initialSettings;
    default:
      return state;
  }
};

// Storage key for persisting settings
const SETTINGS_STORAGE_KEY = 'openKaraokeSettings';

// Provider component
export const SettingsProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  // Load settings from localStorage on initial render
  const loadedSettings = (() => {
    try {
      const storedSettings = localStorage.getItem(SETTINGS_STORAGE_KEY);
      if (storedSettings) {
        return JSON.parse(storedSettings) as AppSettings;
      }
    } catch (error) {
      console.error('Failed to load settings from localStorage:', error);
    }
    return initialSettings;
  })();

  const [settings, dispatch] = useReducer(settingsReducer, loadedSettings);

  // Save settings to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings));
    } catch (error) {
      console.error('Failed to save settings to localStorage:', error);
    }
  }, [settings]);

  return (
    <SettingsContext.Provider value={{ settings, dispatch }}>
      {children}
    </SettingsContext.Provider>
  );
};

// Custom hook to use the settings context
export const useSettings = () => {
  const context = useContext(SettingsContext);
  if (context === undefined) {
    throw new Error('useSettings must be used within a SettingsProvider');
  }
  return context;
};
