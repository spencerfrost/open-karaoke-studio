export type SongStatus = 'processing' | 'queued' | 'processed' | 'error';

export interface Song {
  id: string;
  title: string;
  artist: string;
  duration: number; // in seconds
  status: SongStatus;
  favorite: boolean;
  dateAdded: string;
  coverArt?: string;
  vocalPath?: string;
  instrumentalPath?: string;
  originalPath?: string;
}

export interface SongProcessingRequest {
  file: File;
  title?: string;
  artist?: string;
}

export interface SongProcessingStatus {
  id: string;
  progress: number; // 0-100
  status: SongStatus;
  message?: string;
}
