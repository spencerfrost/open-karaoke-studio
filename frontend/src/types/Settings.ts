export interface ThemeSettings {
  darkMode: boolean;
  themeName: "vintage" | "synthwave" | "minimal";
}

export interface AudioSettings {
  defaultVocalVolume: number; // 0-100
  defaultInstrumentalVolume: number; // 0-100
  fadeInDuration: number; // in milliseconds
  fadeOutDuration: number; // in milliseconds
}

export interface ProcessingSettings {
  quality: "low" | "medium" | "high";
  outputFormat: "mp3" | "wav";
  autoProcessYouTube: boolean;
}

export interface DisplaySettings {
  lyricsSize: "small" | "medium" | "large";
  showAudioVisualizations: boolean;
  showProgress: boolean;
}

export interface AppSettings {
  theme: ThemeSettings;
  audio: AudioSettings;
  processing: ProcessingSettings;
  display: DisplaySettings;
}
