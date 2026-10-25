/**
 * useAddFlowNavigation - moving between the add-song screens, wherever they run.
 *
 * The add flow is three screens: search, an artist, an album. On the phone
 * they are routes (`/add?q=…`, `/add/artist/:browseId`, `/add/album/:browseId`)
 * so the back button and links work; on the stage they are a stack inside the
 * shell, because the player underneath must keep playing. Screens call these
 * functions and never have to know which.
 */

import { useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useStageShell } from "@/features/stage";

export type AddFlowStep =
  | {
      kind: "search";
      query?: string;
      /**
       * Opened from the library's "Browse artist": go straight to the artist
       * whose name matches the query exactly, if there is one.
       */
      findArtist?: boolean;
      /**
       * Picked from the suggestions: when YouTube Music's top result for the
       * query is an artist, open them, with these results behind.
       */
      openTopArtist?: boolean;
    }
  | { kind: "artist"; browseId: string; backLabel?: string }
  | { kind: "album"; browseId: string; backLabel?: string };

interface OpenOptions {
  /** What the next screen's back link says, e.g. `Results for "queen"`. */
  backLabel?: string;
  /** Take this screen's place instead of stacking on it. */
  replace?: boolean;
}

/** Where back goes when there's no screen behind this one (a link opened cold). */
const fallbackPath = (step: AddFlowStep) =>
  step.kind === "search" ? "/" : "/add";

export const addFlowPath = (step: AddFlowStep): string => {
  if (step.kind === "artist") return `/add/artist/${step.browseId}`;
  if (step.kind === "album") return `/add/album/${step.browseId}`;
  const params = new URLSearchParams();
  if (step.query) params.set("q", step.query);
  if (step.findArtist) params.set("findArtist", "1");
  if (step.openTopArtist) params.set("openTopArtist", "1");
  const search = params.toString();
  return search ? `/add?${search}` : "/add";
};

export const useAddFlowNavigation = () => {
  const navigate = useNavigate();
  const shell = useStageShell();

  const open = useCallback(
    (step: AddFlowStep, { replace = false }: { replace?: boolean } = {}) => {
      if (shell) {
        if (replace) shell.replaceAdd(step);
        else shell.pushAdd(step);
        return;
      }
      const backLabel = step.kind === "search" ? undefined : step.backLabel;
      navigate(addFlowPath(step), { replace, state: { backLabel } });
    },
    [navigate, shell],
  );

  const back = useCallback(
    (from: AddFlowStep) => {
      if (shell) {
        shell.back();
        return;
      }
      // React Router numbers its history entries; 0 is the first in this tab.
      const idx = (window.history.state as { idx?: number } | null)?.idx ?? 0;
      if (idx > 0) navigate(-1);
      else navigate(fallbackPath(from), { replace: true });
    },
    [navigate, shell],
  );

  return useMemo(
    () => ({
      /** Show results for a query, in place of the current search. */
      search: (query: string, opts: { openTopArtist?: boolean } = {}) =>
        open(
          { kind: "search", query, openTopArtist: opts.openTopArtist },
          { replace: true },
        ),
      openArtist: (browseId: string, opts: OpenOptions = {}) =>
        open(
          { kind: "artist", browseId, backLabel: opts.backLabel },
          { replace: opts.replace },
        ),
      openAlbum: (browseId: string, opts: OpenOptions = {}) =>
        open(
          { kind: "album", browseId, backLabel: opts.backLabel },
          { replace: opts.replace },
        ),
      back,
    }),
    [open, back],
  );
};
