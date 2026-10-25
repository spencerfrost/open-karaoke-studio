/**
 * useOpenAddSong - "take me to the add-song flow", wherever we happen to be.
 *
 * On the phone and desktop that is a route change; on the stage it is a screen
 * change inside the shell, because the player underneath must keep playing.
 * Callers get one function and never have to know which. Moving around inside
 * the flow is useAddFlowNavigation's job.
 */

import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useStageShell } from "@/features/stage";
import { addFlowPath } from "./useAddFlowNavigation";

export interface OpenAddSongOptions {
  query?: string;
  /** Go straight to the artist whose name matches `query`, if there is one. */
  findArtist?: boolean;
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
      navigate(addFlowPath({ kind: "search", ...opts }));
    },
    [navigate, shell],
  );
};
