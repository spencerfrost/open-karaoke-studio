import { YouTubeMusicSong } from "@/types/YouTubeMusic";

export interface YouTubeMusicSearchProps {
  className?: string;
}

export interface SearchInputProps {
  query: string;
  onQueryChange: (query: string) => void;
  placeholder?: string;
}

export interface SearchResultsProps {
  results: YouTubeMusicSong[];
  isLoading: boolean;
  error: Error | null;
  query: string;
  onAddToLibrary: (song: YouTubeMusicSong) => void;
  addingStates: Record<string, boolean>;
}

export interface SongResultItemProps {
  song: YouTubeMusicSong;
  isAdding: boolean;
  onAddToLibrary: (song: YouTubeMusicSong) => void;
}

export interface AddSongDialogProps {
  isOpen: boolean;
  onClose: () => void;
  selectedSong: YouTubeMusicSong | null;
  onConfirm: () => void;
}