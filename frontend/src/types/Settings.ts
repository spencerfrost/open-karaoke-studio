import type { ThemeName } from "@/lib/themes";

export interface ThemeSettings {
  themeName: ThemeName;
}

export interface AudioSettings {
  defaultVocalVolume: number; // 0-100
  defaultInstrumentalVolume: number; // 0-100
  fadeInDuration: number; // in milliseconds
  fadeOutDuration: number; // in milliseconds
  // Audio outputs. All optional for the same shallow-merge reason as
  // DisplaySettings.songPreviewsEnabled; read them through getAudioOutputs.
  // Device ids come from enumerateDevices; null or missing = the system
  // default for the speakers, and off for the headphones.
  speakersDeviceId?: string | null;
  /** The device's name when chosen, shown while it is unplugged. */
  speakersDeviceLabel?: string;
  /** The singer's headphones: the lead vocal alone, on a second output. */
  headphonesDeviceId?: string | null;
  headphonesDeviceLabel?: string;
  /** Extra wait for the headphones, matching the speakers' own lag. */
  headphonesDelayMs?: number;
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
