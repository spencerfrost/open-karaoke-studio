/**
 * StageShell - stage mode: a full-screen app with screens, not a page with a nav bar.
 *
 * Two resting states, song select and performance, plus a confirm step and an
 * add-song detour. They are component state rather than routes for one reason
 * that decides the whole design: **the performance screen never unmounts.**
 * Someone browsing mid-song must come back to the same audio, the same lyrics
 * timing, the same open dialogs — so the player is hidden while another screen
 * is up, the way the rails already collapse without unmounting.
 *
 * Hidden rather than covered: an opaque screen layered on top still leaves the
 * browser laying out and painting the player underneath it.
 *
 * The fullscreen container lives here rather than on StageLayout, so every
 * screen is inside it; anything mounted outside would vanish in full screen.
 */

import React, { useCallback, useMemo, useState } from "react";
import { StageLayout } from "@/features/player/components/stage";
import { usePlayerUI } from "@/features/player/hooks";
import { useRoster } from "@/hooks/api/useRoster";
import { useSessionStore } from "@/stores/sessionStore";
import { cn } from "@/lib/utils";
import type { KaraokeQueueItemWithSong } from "@/types/KaraokeQueue";
import type { Song } from "@/types/Song";
import {
  StageShellContext,
  StageScreenContext,
  type StageScreen,
  type StageShellApi,
} from "./StageShellContext";
import ExitStagePrompt from "./ExitStagePrompt";
import SongSelectScreen from "./screens/SongSelectScreen";
import SongConfirmScreen from "./screens/SongConfirmScreen";
import AddSongScreen from "./screens/AddSongScreen";

interface StageShellProps {
  songId: string;
  current?: KaraokeQueueItemWithSong | null;
  upcoming: KaraokeQueueItemWithSong[];
  queueItems?: KaraokeQueueItemWithSong[];
  onPlayFromQueue: (id: string) => void;
  onRemoveFromQueue: (id: string) => void;
}

const StageShell: React.FC<StageShellProps> = ({
  songId,
  current,
  upcoming,
  queueItems,
  onPlayFromQueue,
  onRemoveFromQueue,
}) => {
  const ui = usePlayerUI();
  const [screen, setScreen] = useState<StageScreen>({ name: "performance" });
  const [isExitPromptOpen, setIsExitPromptOpen] = useState(false);
  const { displayCode } = useSessionStore();
  const rosterQuery = useRoster(displayCode || undefined);
  const roster = useMemo(() => rosterQuery.data ?? [], [rosterQuery.data]);

  const openPerformance = useCallback(
    () => setScreen({ name: "performance" }),
    [],
  );
  const openSelect = useCallback(
    (opts: { expandArtist?: string } = {}) =>
      setScreen({ name: "select", expandArtist: opts.expandArtist }),
    [],
  );
  const openConfirm = useCallback(
    (song: Song) => setScreen({ name: "confirm", song }),
    [],
  );
  const openAdd = useCallback(
    (opts: { query?: string; browseArtist?: boolean } = {}) =>
      setScreen({
        name: "add",
        query: opts.query,
        browseArtist: opts.browseArtist,
      }),
    [],
  );

  // Confirm and add are detours off song select; song select falls back to the
  // player. There is no deeper history to keep, which is the point.
  const back = useCallback(() => {
    setScreen((current_) =>
      current_.name === "select" ? { name: "performance" } : { name: "select" },
    );
  }, []);

  // Constant for the life of the shell: every setter is a stable useCallback and
  // nothing that varies lives in here. Several hundred song cards and artist
  // rows consume this, so a new identity per screen change would re-render the
  // whole library on the way out of it.
  const shellApi = useMemo<StageShellApi>(
    () => ({ openPerformance, openSelect, openConfirm, openAdd, back }),
    [openPerformance, openSelect, openConfirm, openAdd, back],
  );

  const isPerforming = screen.name === "performance";

  // Song select is mounted once and then only ever hidden. It is ~600 artist
  // rows, each holding two React Query observers, so mounting it costs seconds
  // on a full library — far too much to pay every time someone taps Back. Kept
  // mounted it also keeps its scroll position and expanded rows.
  //
  // Add and confirm stay mount-on-demand: both are cheap, and the add screen
  // seeds its search box from `query` on mount only, so it has to remount to
  // pick up a new one.
  const [selectMounted, setSelectMounted] = useState(false);
  if (screen.name === "select" && !selectMounted) setSelectMounted(true);

  // Stable so the memoized select screen is not re-rendered by an inline arrow.
  const handleExitStage = useCallback(() => setIsExitPromptOpen(true), []);

  const handleLeaveStage = useCallback(() => {
    if (ui.isFullscreen) ui.toggleFullscreen();
  }, [ui]);

  return (
    <StageShellContext.Provider value={shellApi}>
      <StageScreenContext.Provider value={screen}>
        <div
          ref={ui.containerRef}
          className="relative h-full w-full overflow-hidden"
          style={{ background: "var(--page-bg)" }}
        >
          {/* Painted once, for every screen. Both of these are expensive - a
            full-viewport repeating-conic-gradient and a tiled SVG - so a
            second copy stacked over the first made every repaint, down to
            expanding an accordion row, visibly slow. */}
          <div className="vintage-sunburst-pattern" />
          <div className="vintage-texture-overlay" />
          <div className="absolute inset-0 z-[11] bg-overlay/85" />

          {/* Always mounted, `hidden` while another screen is up. Same discipline
            the rails already use: React state, dialogs and audio all survive,
            but display:none means the covered player costs no layout or paint
            - and the lyrics stop repainting 60x/sec behind the library. */}
          <div
            className={cn(
              "relative z-20 h-full w-full",
              !isPerforming && "hidden",
            )}
          >
            <StageLayout
              songId={songId}
              current={current}
              upcoming={upcoming}
              queueItems={queueItems}
              onPlayFromQueue={onPlayFromQueue}
              onRemoveFromQueue={onRemoveFromQueue}
              ui={ui}
              keyboardEnabled={isPerforming}
            />
          </div>

          {selectMounted && (
            <div
              className={cn(
                "absolute inset-0 z-20 overflow-hidden",
                screen.name !== "select" && "hidden",
              )}
            >
              <SongSelectScreen
                expandArtist={
                  screen.name === "select" ? screen.expandArtist : undefined
                }
                hasCurrentSong={Boolean(current)}
                onExitStage={handleExitStage}
              />
            </div>
          )}

          {screen.name === "confirm" && (
            <div className="absolute inset-0 z-20 overflow-hidden">
              <SongConfirmScreen song={screen.song} roster={roster} />
            </div>
          )}

          {screen.name === "add" && (
            <div className="absolute inset-0 z-20 overflow-hidden">
              <AddSongScreen
                query={screen.query}
                browseArtist={screen.browseArtist}
              />
            </div>
          )}

          <ExitStagePrompt
            isOpen={isExitPromptOpen}
            onClose={() => setIsExitPromptOpen(false)}
            onLeaveStage={handleLeaveStage}
          />
        </div>
      </StageScreenContext.Provider>
    </StageShellContext.Provider>
  );
};

export default StageShell;
