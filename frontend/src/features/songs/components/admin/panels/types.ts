import { Song } from "@/types/Song";

export interface ReplacePanelProps {
  song: Song;
  onDone: () => void;
}

export interface FingerprintCandidate {
  score: number;
  recordingId: string;
  title: string;
  artist: string;
  album?: string | null;
  year?: number | null;
  duration?: number | null;
}

export interface ValidationResult {
  validated: boolean;
  acoustidStatus: string;
  acoustidScore: number | null;
  musicbrainzId: string | null;
  title: string | null;
  artist: string | null;
  message: string;
}

export interface MusicBrainzResult {
  score: number;
  recordingId: string;
  title: string;
  artist: string;
  album: string;
  releaseDate: string;
  duration: number | null;
}
