import { YoutubeVideoSearchResult } from "@/types/Youtube";
import { YoutubeMusicSearchResult } from "@/types/Youtube";

// Base search source type
export type SearchSource = "youtube-music" | "youtube";

export type SearchResult = YoutubeMusicSearchResult | YoutubeVideoSearchResult;

// Type guards for search results
export const isYouTubeMusicResult = (
  result: SearchResult,
): result is YoutubeMusicSearchResult => {
  return "videoId" in result && "thumbnails" in result;
};

export const isYouTubeResult = (
  result: SearchResult,
): result is YoutubeVideoSearchResult => {
  return "id" in result && "uploader" in result && !("videoId" in result);
};

// Component prop interfaces
export interface SongSearchContainerProps {
  className?: string;
}

export interface SearchInputProps {
  query: string;
  onSearch: (query: string) => void;
  placeholder?: string;
  disabled?: boolean;
}

export interface SearchTabsProps {
  activeSource: SearchSource;
  onSourceChange: (source: SearchSource) => void;
  counts: Record<SearchSource, number>;
}

export interface SearchResultsProps {
  source: SearchSource;
  results: SearchResult[];
  isLoading: boolean;
  error: Error | null;
  onSelect: (result: SearchResult, source: SearchSource) => void;
  loadingStates: Record<string, boolean>;
}

export interface YouTubeResultsProps {
  results: YoutubeVideoSearchResult[];
  isLoading: boolean;
  error: Error | null;
  onSelect: (result: YoutubeVideoSearchResult) => void;
  loadingStates: Record<string, boolean>;
}

export interface YouTubeResultCardProps {
  result: YoutubeVideoSearchResult;
  isLoading: boolean;
  onSelect: (result: YoutubeVideoSearchResult) => void;
}

// Search refinement types for dialog
export interface SearchRefinementInputProps {
  query: string;
  onQueryChange: (query: string) => void;
  placeholder?: string;
  label?: string;
  description?: string;
}

export interface SongCreationData {
  result: SearchResult;
  source: SearchSource;
  originalQuery?: string;
}

export interface AddSongDialogProps {
  isOpen: boolean;
  onClose: () => void;
  selectedSong: YoutubeMusicSearchResult | null;
  onConfirm: () => void;
}
