/**
 * Fixing a line of lyrics on the stage: which song may be fixed, which line
 * is open in the editor, and which line is being sung (for the keyboard's
 * "fix the current line").
 *
 * Local UI state for the one screen showing the stage, so it isn't keyed by
 * session. The stage turns it on for its song; everywhere else the lyrics
 * render with no fix button.
 */

import { create } from "zustand";

/** A lyric line as the screen shows it: its LRC time (ms) and its text. */
export interface FixableLine {
  timestamp: number;
  content: string;
}

interface LineFixState {
  /** The song whose lines can be fixed; null hides every fix button. */
  songId: string | null;
  /** The line open in the editor. */
  editing: FixableLine | null;
  /** The line being sung right now, kept by the lyrics renderer. */
  activeLine: FixableLine | null;
  enable: (songId: string | null) => void;
  startEditing: (line: FixableLine) => void;
  stopEditing: () => void;
  setActiveLine: (line: FixableLine | null) => void;
}

export const useLineFixStore = create<LineFixState>((set, get) => ({
  songId: null,
  editing: null,
  activeLine: null,
  enable: (songId) => {
    if (get().songId === songId) return;
    // A new song closes the editor: its line belongs to the old one.
    set({ songId, editing: null, activeLine: null });
  },
  startEditing: (line) => {
    if (get().songId === null || !line.content.trim()) return;
    set({ editing: { timestamp: line.timestamp, content: line.content } });
  },
  stopEditing: () => set({ editing: null }),
  setActiveLine: (line) => set({ activeLine: line }),
}));

export const isSameLine = (
  a: FixableLine | null,
  b: FixableLine | null,
): boolean =>
  a !== null &&
  b !== null &&
  a.timestamp === b.timestamp &&
  a.content === b.content;
