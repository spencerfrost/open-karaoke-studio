/**
 * The singers in the queue. Maya's song is the video's soundtrack; the rest
 * are made up.
 */
export interface QueuedSong {
  singer: string;
  title: string;
  artist: string;
  /** Cover gradient hues. */
  hues: [number, number];
  avatar: string;
}

export const QUEUE: QueuedSong[] = [
  { singer: "Maya", title: "Don't Blink", artist: "Dropical", hues: [330, 270], avatar: "#ff2a6d" },
  { singer: "Jordan", title: "Heartbeat Highway", artist: "Velvet Static", hues: [20, 340], avatar: "#fcee0a" },
  { singer: "Priya", title: "Golden Hour", artist: "Lumen Park", hues: [45, 15], avatar: "#39ff88" },
  { singer: "Sam", title: "Don't Stop the Night", artist: "Coastline", hues: [260, 200], avatar: "#b07bff" },
  { singer: "Alex", title: "Satellite Love", artist: "Nova Kids", hues: [300, 230], avatar: "#ff8a3d" },
];
