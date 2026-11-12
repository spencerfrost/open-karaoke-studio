/**
 * StageShell - stage mode: a full-screen app with screens, not a page with a nav bar.
 *
 * Two resting states, song select and performance, plus a confirm step, an
 * add-song detour and the handoff screen between songs. They are component
 * state rather than routes for one reason
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

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { StageLayout } from "@/features/player/components/stage";
import { usePlayerUI } from "@/features/player/hooks";
import { useRoster } from "@/hooks/api/useRoster";
import { useJobTrackerStore } from "@/stores/jobTrackerStore";
import { useSessionStore } from "@/stores/sessionStore";
import { usePlaybackStateStore } from "@/stores/usePlaybackStateStore";
import { cn } from "@/lib/utils";
import type {
  KaraokeQueueItemWithSong,
  SessionTurn,
} from "@/types/KaraokeQueue";
import type { Song } from "@/types/Song";
import type { AddFlowStep } from "@/hooks/useAddFlowNavigation";
import type { OpenAddSongOptions } from "@/hooks/useOpenAddSong";
import {
  StageShellContext,
  StageScreenContext,
  StageQueueContext,
  type StageQueue,
  type StageScreen,
  type StageShellApi,
} from "./StageShellContext";
import ExitStagePrompt from "./ExitStagePrompt";
import SongSelectScreen from "./screens/SongSelectScreen";
import SongConfirmScreen from "./screens/SongConfirmScreen";
import AddSongScreen from "./screens/AddSongScreen";
import HandoffScreen from "./screens/HandoffScreen";
import OpenYourPhonePrompt from "./components/OpenYourPhonePrompt";
import { GuidedTour } from "@/features/tour";
import { findTurnItem } from "./turnItem";

interface StageShellProps {
  songId: string;
  current?: KaraokeQueueItemWithSong | null;
  upcoming: KaraokeQueueItemWithSong[];
  onPlayFromQueue: (id: string) => void;
  onRemoveFromQueue: (id: string) => void;
  /** Whose turn it is, computed by the server. The handoff screen renders it. */
  turn: SessionTurn;
}

/** How far into a song, as a fraction, before song select opens fresh. */
const WHEEL_FRESH_AT = 0.1;
/** Song select and the detours off it: the wheel is in someone's hands. */
const BROWSING_SCREENS = new Set<StageScreen["name"]>([
  "select",
  "confirm",
  "add",
]);

const StageShell: React.FC<StageShellProps> = ({
  songId,
  current,
  upcoming,
  onPlayFromQueue,
  onRemoveFromQueue,
  turn,
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
    (opts: OpenAddSongOptions = {}) =>
      setScreen({
        name: "add",
        stack: [
          opts.artistBrowseId
            ? {
                kind: "artist",
                browseId: opts.artistBrowseId,
                backLabel: "Songbook",
              }
            : {
                kind: "search",
                query: opts.query,
                findArtist: opts.findArtist,
              },
        ],
      }),
    [],
  );
  // Both only act inside the add flow; elsewhere there's no stack to change.
  const pushAdd = useCallback(
    (step: AddFlowStep) =>
      setScreen((s) =>
        s.name === "add" ? { name: "add", stack: [...s.stack, step] } : s,
      ),
    [],
  );
  const replaceAdd = useCallback(
    (step: AddFlowStep) =>
      setScreen((s) =>
        s.name === "add"
          ? { name: "add", stack: [...s.stack.slice(0, -1), step] }
          : s,
      ),
    [],
  );
  const openHandoff = useCallback(() => setScreen({ name: "handoff" }), []);

  // The one screen the shell drives itself. A song ending is not a tap, and the
  // gap it opens is the moment the whole rotation exists for - so the shell
  // watches for it rather than waiting to be told.
  //
  // Only from the performance screen: someone browsing the library when a song
  // runs out should not be yanked away mid-scroll.
  const songEnded = usePlaybackStateStore((state) => state.songEnded);
  useEffect(() => {
    if (songEnded) {
      setScreen((s) => (s.name === "performance" ? { name: "handoff" } : s));
    } else {
      setScreen((s) => (s.name === "handoff" ? { name: "performance" } : s));
    }
  }, [songEnded]);

  // Read by `back` rather than listed as its dependencies: both change on
  // every queue broadcast, and the shell API must keep one identity.
  const queueRef = useRef({ turn, upcoming });
  queueRef.current = { turn, upcoming };

  // Confirm and add are detours off song select; song select falls back to the
  // player. The add flow walks back through its own screens (album, artist,
  // search) first; otherwise there is no deeper history to keep, which is the
  // point.
  //
  // Unless the song has ended: the player would only show a finished song. If
  // the next singer has a song, their handoff screen is the place to be;
  // otherwise the library is, so stay in it.
  //
  // openPerformance itself stays unconditional. "Sing it now" calls it before
  // the new song has loaded, while songEnded still describes the old one.
  const back = useCallback(() => {
    setScreen((current_) => {
      if (current_.name === "add" && current_.stack.length > 1) {
        return { name: "add", stack: current_.stack.slice(0, -1) };
      }
      if (current_.name !== "select") return { name: "select" };
      if (!usePlaybackStateStore.getState().songEnded) {
        return { name: "performance" };
      }
      const { turn: turn_, upcoming: upcoming_ } = queueRef.current;
      return findTurnItem(turn_, upcoming_) ? { name: "handoff" } : current_;
    });
  }, []);

  // Constant for the life of the shell: every setter is a stable useCallback and
  // nothing that varies lives in here. Several hundred song cards and artist
  // rows consume this, so a new identity per screen change would re-render the
  // whole library on the way out of it.
  const shellApi = useMemo<StageShellApi>(
    () => ({
      openPerformance,
      openSelect,
      openConfirm,
      openAdd,
      pushAdd,
      replaceAdd,
      openHandoff,
      back,
    }),
    [
      openPerformance,
      openSelect,
      openConfirm,
      openAdd,
      pushAdd,
      replaceAdd,
      openHandoff,
      back,
    ],
  );

  const stageQueue = useMemo<StageQueue>(
    () => ({ current: current ?? null, upcoming, turn }),
    [current, upcoming, turn],
  );

  // A finished song that reaches the queue by any route - "Sing this", the
  // wheel, a phone - has done its job in the processing list. Watched here
  // rather than in the list, which is only mounted on song select.
  const dismissFinished = useJobTrackerStore((s) => s.dismissFinished);
  useEffect(() => {
    const queued = upcoming.map((item) => item.songId);
    if (current) queued.push(current.songId);
    dismissFinished(queued);
  }, [current, upcoming, dismissFinished]);

  const isPerforming = screen.name === "performance";

  // Song select is mounted once and then only ever hidden, so the wheel keeps
  // its place across a trip to confirm and back. This used to be forced: the
  // old accordion was ~600 artist rows with two React Query observers each and
  // took seconds to mount. The wheel renders ~40 rows, so remounting it once
  // per singer (below) is cheap.
  //
  // Add and confirm stay mount-on-demand: both are cheap, and a fresh trip
  // into the add flow should start from a fresh search.
  const [selectMounted, setSelectMounted] = useState(false);
  if (screen.name === "select" && !selectMounted) setSelectMounted(true);

  // The wheel's place belongs to one singer. Until the song is a little way in,
  // whoever comes back to song select is most likely the singer who picked it,
  // after a different song by the same artist, so the place is kept. Past that
  // mark the next person is the one browsing, and song select opens fresh.
  //
  // Not while the wheel is in use: someone already browsing when the mark
  // passes is the next singer, and keeps their place.
  const pastFreshMark = usePlaybackStateStore(
    (state) =>
      state.duration > 0 &&
      state.currentTime >= state.duration * WHEEL_FRESH_AT,
  );
  const [seenPastFreshMark, setSeenPastFreshMark] = useState(pastFreshMark);
  const [wheelStale, setWheelStale] = useState(false);
  const [selectKey, setSelectKey] = useState(0);
  if (pastFreshMark !== seenPastFreshMark) {
    setSeenPastFreshMark(pastFreshMark);
    if (pastFreshMark && !BROWSING_SCREENS.has(screen.name)) {
      setWheelStale(true);
    }
  }
  if (screen.name === "select" && wheelStale) {
    setWheelStale(false);
    setSelectKey((key) => key + 1);
  }

  // Stable so the memoized select screen is not re-rendered by an inline arrow.
  const handleExitStage = useCallback(() => setIsExitPromptOpen(true), []);

  const handleLeaveStage = useCallback(() => {
    if (ui.isFullscreen) ui.toggleFullscreen();
  }, [ui]);

  return (
    <StageShellContext.Provider value={shellApi}>
      <StageScreenContext.Provider value={screen}>
        <StageQueueContext.Provider value={stageQueue}>
          <div
            ref={ui.containerRef}
            className="relative h-full w-full overflow-hidden"
            style={{ background: "var(--page-bg)" }}
          >
            {/* Painted once, for every screen. Both of these are expensive - a
            full-viewport repeating-conic-gradient and a tiled SVG - so a
            second copy stacked over the first made every repaint, down to
            expanding an accordion row, visibly slow. */}
            <div className="theme-pattern" />
            <div className="theme-texture" />
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
                onPlayFromQueue={onPlayFromQueue}
                onRemoveFromQueue={onRemoveFromQueue}
                ui={ui}
                keyboardEnabled={isPerforming}
              />
              <OpenYourPhonePrompt current={current} />
            </div>

            {selectMounted && (
              <div
                className={cn(
                  "absolute inset-0 z-20 overflow-hidden",
                  screen.name !== "select" && "hidden",
                )}
              >
                <SongSelectScreen
                  key={selectKey}
                  active={screen.name === "select"}
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
                <SongConfirmScreen
                  song={screen.song}
                  roster={roster}
                  turn={turn}
                />
              </div>
            )}

            {screen.name === "handoff" && (
              <div className="absolute inset-0 z-20 overflow-hidden">
                <HandoffScreen
                  current={current}
                  upcoming={upcoming}
                  turn={turn}
                  roster={roster}
                  onPlayFromQueue={onPlayFromQueue}
                />
              </div>
            )}

            {screen.name === "add" && (
              <div className="absolute inset-0 z-20 overflow-hidden">
                <AddSongScreen step={screen.stack[screen.stack.length - 1]} />
              </div>
            )}

            <ExitStagePrompt
              isOpen={isExitPromptOpen}
              onClose={() => setIsExitPromptOpen(false)}
              onLeaveStage={handleLeaveStage}
            />

            {/* The live demo's guided tour. Renders nothing outside a demo
                session. Inside the full-screen container, like everything. */}
            <GuidedTour />
          </div>
        </StageQueueContext.Provider>
      </StageScreenContext.Provider>
    </StageShellContext.Provider>
  );
};

export default StageShell;
