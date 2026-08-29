import { KaraokeQueueItemWithSong } from "./KaraokeQueue";

export type PlayerStatus = "idle" | "playing" | "paused";

export interface PlayerState {
  status: PlayerStatus;
  currentTime: number;
  duration: number;
  vocalVolume: number;
  instrumentalVolume: number;
  currentSong: KaraokeQueueItemWithSong | null;
}
