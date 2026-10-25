/**
 * AddSongProvider - supplies the add flow's submissions (see addSongContext),
 * and what to do once a song is added.
 */

import React, { useMemo } from "react";
import { useSongCreation } from "../../hooks/useSongCreation";
import { AddSongContext, type AddSongContextValue } from "./addSongContext";

interface AddSongProviderProps {
  /** Called after a song is added, e.g. the stage handing back to song select. */
  onAdded?: () => void;
  children: React.ReactNode;
}

export const AddSongProvider: React.FC<AddSongProviderProps> = ({
  onAdded,
  children,
}) => {
  const { addSong, getSubmission } = useSongCreation();

  const value = useMemo<AddSongContextValue>(
    () => ({
      addSong: (song, source) => {
        if (!song.videoId || !song.title) return;
        void addSong({
          videoId: song.videoId,
          title: song.title,
          artists: song.artists.map((a) => ({
            name: a.name,
            id: a.id ?? null,
          })),
          album: song.album,
          durationSeconds: song.durationSeconds,
          source,
        }).then((songId) => {
          if (songId) onAdded?.();
        });
      },
      getSubmission,
    }),
    [addSong, getSubmission, onAdded],
  );

  return (
    <AddSongContext.Provider value={value}>{children}</AddSongContext.Provider>
  );
};
