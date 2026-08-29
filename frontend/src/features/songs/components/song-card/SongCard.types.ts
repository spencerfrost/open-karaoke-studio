import { Song } from "@/types/Song";

export interface SongCardProps {
  song: Song;
  onPlay?: (song: Song) => void;
  variant?: "compact" | "detailed";
  actions?: SongCardAction[];
  sessionId?: string;
  showArtist?: boolean;
}

export type SongCardAction = "details" | "queue";

export interface SongArtworkProps {
  song: Song;
  artworkUrl: string | null;
  showSyncedBadge?: boolean;
  /** Shows a "needs review" flag when the song's AcoustID match is ambiguous. Host-only. */
  showAmbiguousBadge?: boolean;
  onPlay: (e?: React.MouseEvent) => void;
  showPlayButton?: boolean;
  /** Enables the hover-to-preview behaviour on this artwork. */
  enablePreview?: boolean;
  /** Renders an explicit preview control, for pointers that cannot hover. */
  showPreviewButton?: boolean;
}

export interface SongInfoProps {
  song: Song;
  showArtist?: boolean;
}
