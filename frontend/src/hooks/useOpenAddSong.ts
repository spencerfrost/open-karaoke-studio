/**
 * useOpenAddSong - "take me to the add-song flow", wherever we happen to be.
 *
 * On the phone and desktop that is a route change; on the stage it is a screen
 * change inside the shell, because the player underneath must keep playing.
 * Callers get one function and never have to know which.
 */

import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useStageShell } from "@/features/stage";

export interface OpenAddSongOptions {
  query?: string;
  browseArtist?: boolean;
}

export const useOpenAddSong = () => {
  const navigate = useNavigate();
  const shell = useStageShell();

  return useCallback(
    (opts: OpenAddSongOptions = {}) => {
      if (shell) {
        shell.openAdd(opts);
        return;
      }

      const params = new URLSearchParams();
      if (opts.query) params.set("q", opts.query);
      if (opts.browseArtist) params.set("browseArtist", "true");

      const search = params.toString();
      navigate(search ? `/add?${search}` : "/add");
    },
    [navigate, shell],
  );
};
