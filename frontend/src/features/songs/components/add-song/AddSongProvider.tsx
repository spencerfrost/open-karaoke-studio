/**
 * AddSongProvider - supplies the add flow's submissions (see addSongContext).
 * Adding a song leaves the guest where they are, so they can add several.
 */

import React, { useMemo } from "react";
import { useSongCreation } from "../../hooks/useSongCreation";
import { AddSongContext, type AddSongContextValue } from "./addSongContext";

interface AddSongProviderProps {
  children: React.ReactNode;
}

export const AddSongProvider: React.FC<AddSongProviderProps> = ({
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
        });
      },
      getSubmission,
    }),
    [addSong, getSubmission],
  );

  return (
    <AddSongContext.Provider value={value}>{children}</AddSongContext.Provider>
  );
};
