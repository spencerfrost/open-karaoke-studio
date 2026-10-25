/**
 * The add-song flow's shared state: this page's submissions, and adding a
 * song. AddSongProvider supplies it, above every screen, so a song added on
 * the artist screen still shows as added after going back to the results.
 */

import { createContext, useContext } from "react";
import type { YoutubeMusicSong } from "@/types/Youtube";
import type { SongInput, SongSubmission } from "../../hooks/useSongCreation";

export interface AddSongContextValue {
  /** Add a song; resolves to its library id, or null when it didn't go. */
  addSong: (song: YoutubeMusicSong, source: SongInput["source"]) => void;
  getSubmission: (videoId: string | null) => SongSubmission | undefined;
}

export const AddSongContext = createContext<AddSongContextValue | null>(null);

export const useAddSong = () => {
  const value = useContext(AddSongContext);
  if (!value) throw new Error("useAddSong needs an AddSongProvider");
  return value;
};

/** What a song's add button shows: see the table in the add-song plan. */
export type SongRowState =
  | { kind: "add" }
  | { kind: "adding" }
  | { kind: "ready"; songId: string }
  | { kind: "processing"; songId: string }
  | { kind: "retry" }
  | { kind: "unavailable" };

export const useSongRowState = (song: YoutubeMusicSong): SongRowState => {
  const { getSubmission } = useAddSong();
  if (!song.videoId) return { kind: "unavailable" };

  const submission = getSubmission(song.videoId);
  if (submission?.status === "adding") return { kind: "adding" };
  if (submission?.status === "added") {
    return { kind: "processing", songId: submission.songId };
  }

  switch (song.library?.status) {
    case "ready":
      return { kind: "ready", songId: song.library.songId };
    case "processing":
      return { kind: "processing", songId: song.library.songId };
    case "failed":
      return { kind: "retry" };
    default:
      return { kind: "add" };
  }
};
