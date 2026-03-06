import { Song } from "./Song";

export interface KaraokeQueueItem {
  id: string;
  songId: string;
  singer: string;
  position: number;
  addedAt: string;
}

export interface KaraokeQueueItemWithSong extends KaraokeQueueItem {
  song: Song;
}

export interface KaraokeQueueState {
  items: KaraokeQueueItemWithSong[];
  currentSong: KaraokeQueueItemWithSong | null;
}

export interface KaraokeQueueStateResponse {
  current: KaraokeQueueItemWithSong | null;
  upcoming: KaraokeQueueItemWithSong[];
  items: KaraokeQueueItemWithSong[];
}

export interface AddToKaraokeQueueRequest {
  songId: string;
  singer: string;
}
