import { Song } from "./Song";

export interface KaraokeQueueItem {
  id: string;
  songId: string;
  singer: string;
  position: number;
  lap: number;
  addedAt: string;
}

export interface KaraokeQueueItemWithSong extends KaraokeQueueItem {
  song: Song;
}

/** A performer as the turn payload names them. */
export interface TurnPerformer {
  id: number;
  name: string;
}

/**
 * Whose turn it is - computed by the server, rendered by the handoff screen.
 *
 * `kind` is the whole state machine:
 * - `queued`     - the next person has a song, and `itemId` points at it in `upcoming`.
 * - `empty_seat` - it is their turn with nothing in it. Not "the queue is over":
 *                  the night is still going, they just have not picked yet.
 * - `open`       - nobody is up. An empty roster, or append mode with an empty queue.
 */
export interface SessionTurn {
  kind: "queued" | "empty_seat" | "open";
  performerId: number | null;
  performerName: string | null;
  itemId: number | null;
  /** Active performers in rotation order. Empty in append mode. */
  circle: TurnPerformer[];
}

export interface KaraokeQueueState {
  items: KaraokeQueueItemWithSong[];
  currentSong: KaraokeQueueItemWithSong | null;
}

export interface KaraokeQueueStateResponse {
  current: KaraokeQueueItemWithSong | null;
  upcoming: KaraokeQueueItemWithSong[];
  items: KaraokeQueueItemWithSong[];
  turn: SessionTurn;
}

export interface AddToKaraokeQueueRequest {
  songId: string;
  singer: string;
}
