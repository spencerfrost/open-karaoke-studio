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
  // Optional on purpose: zustand's persist merges shallowly, so an existing
  // user's stored `display` object replaces the default wholesale and this key
  // reads as undefined. Every read must default it with `?? true`.
  songPreviewsEnabled?: boolean;
}

export interface AppSettings {
  theme: ThemeSettings;
  audio: AudioSettings;
  processing: ProcessingSettings;
  display: DisplaySettings;
}
