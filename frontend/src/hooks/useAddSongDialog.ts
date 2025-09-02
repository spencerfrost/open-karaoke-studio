import { useState } from "react";
import type { LyricsOption } from "@/hooks/api/useLyrics";

export const useAddSongDialog = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedLyrics, setSelectedLyrics] = useState<LyricsOption | null>(
    null,
  );

  const openDialog = () => {
    setIsOpen(true);
    setSelectedLyrics(null); // Reset lyrics selection
  };

  const closeDialog = () => {
    setIsOpen(false);
    setSelectedLyrics(null);
  };

  const selectLyrics = (lyrics: LyricsOption | null) => {
    setSelectedLyrics(lyrics);
  };

  return {
    isOpen,
    selectedLyrics,
    openDialog,
    closeDialog,
    selectLyrics,
  };
};
