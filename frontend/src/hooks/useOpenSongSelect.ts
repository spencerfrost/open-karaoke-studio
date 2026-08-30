/**
 * useOpenSongSelect - "take me back to the library", wherever we happen to be.
 *
 * The stage renders the library as a screen over the still-mounted player; the
 * phone and desktop navigate to it. Note the route is `/`, not `/library`:
 * several call sites used to navigate to `/library`, which is not a route and
 * only worked via the catch-all redirect — which dropped `?expandArtist=` on
 * the way.
 */

import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useStageShell } from "@/features/stage";

export interface OpenSongSelectOptions {
  expandArtist?: string;
}

export const useOpenSongSelect = () => {
  const navigate = useNavigate();
  const shell = useStageShell();

  return useCallback(
    (opts: OpenSongSelectOptions = {}) => {
      if (shell) {
        shell.openSelect(opts);
        return;
      }

      navigate(
        opts.expandArtist
          ? `/?expandArtist=${encodeURIComponent(opts.expandArtist)}`
          : "/",
      );
    },
    [navigate, shell],
  );
};
