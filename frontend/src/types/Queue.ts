import { Song } from './Song';

export interface QueueItem {
  id: string;
  songId: string;
  singer: string;
  position: number;
  addedAt: string;
}

export interface QueueItemWithSong extends QueueItem {
  song: Song;
}

export interface QueueState {
  items: QueueItemWithSong[];
  currentItem: QueueItemWithSong | null;
}

export interface AddToQueueRequest {
  songId: string;
  singer: string;
}
