import { Song } from "@/types/Song";

export interface SongCardProps {
  song: Song;
  onPlay?: (song: Song) => void;
  variant?: "compact" | "detailed";
  actions?: SongCardAction[];
  sessionId?: string;
}

export type SongCardAction = "delete" | "details" | "queue";

export interface SongArtworkProps {
  song: Song;
  artworkUrl: string | null;
  showSyncedBadge?: boolean;
  onPlay: (e?: React.MouseEvent) => void;
  showPlayButton?: boolean;
}

export interface SongActionsProps {
  song: Song;
  onQueue?: (e: React.MouseEvent) => void;
  onDelete?: (e: React.MouseEvent) => void;
  onDetails?: (e: React.MouseEvent) => void;
}

export interface SongInfoProps {
  song: Song;
}
