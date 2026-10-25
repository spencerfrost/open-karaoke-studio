/**
 * StageLayout - the stage itself: three columns filling the viewport.
 *
 * Left rail is the same ControlsStrip the phone renders; the centre column is
 * the player; the right rail is the queue. The transport sits under the centre
 * column only, so the rails keep the full height.
 *
 * While a song plays the rails collapse to icon strips and the chrome dims —
 * but nothing unmounts, so dialogs, drag state and focus all survive. The join
 * QR is the exception to the dimming: it shrinks into the foot of the right
 * rail and stays fully visible, so latecomers can always scan in.
 *
 * The backdrop (sunburst, texture, scrim) belongs to the shell, not here: it is
 * shared with every other stage screen, and painting a second full-viewport
 * copy of it per screen is expensive enough to be felt on every click.
 */

import React, { useCallback } from "react";
import { ControlsStrip } from "@/features/performance/controls";
import { useOpenSongSelect } from "@/hooks/useOpenSongSelect";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { cn } from "@/lib/utils";
import type { PlayerUIHook } from "../../types/KaraokePlayer.types";
import KaraokePlayer from "../KaraokePlayer";
import StageTransport from "./StageTransport";
import StageAmbientBar, { STAGE_AMBIENT_BAR_HEIGHT } from "./StageAmbientBar";
import StageJoinCode from "./StageJoinCode";
import StageQueueRail from "./StageQueueRail";
import StageRailIcons from "./StageRailIcons";
import { useStageRails } from "./useStageRails";
import { useStageKeyboard } from "./useStageKeyboard";
import { useStageRootScale } from "./useStageRootScale";
import type { KaraokeQueueItemWithSong } from "@/types/KaraokeQueue";

// rem, so the rails scale with the stage (see useStageRootScale). About 15% of
// the width each: the lyrics are the show, the rails are for whoever walks up
// to the mic.
const RAIL_OPEN = "17rem";
const RAIL_COLLAPSED = "6rem";
// While collapsed the transport gives its height back to the lyrics, keeping
// only what the ambient bar covers below the grid's own bottom padding (p-6).
const COLLAPSED_TRANSPORT_RESERVE = `calc(${STAGE_AMBIENT_BAR_HEIGHT} - 1.5rem)`;
// The join QR clears the ambient bar by a further 1rem: a waveform bar drawn
// over its edge could stop it scanning.
// Wider than the collapsed rail: it spills 1rem into the gap and the outer
// padding on each side (1.5rem each), which reads better from the couch.
const COLLAPSED_JOIN_CODE_SIZE = "7rem";
const COLLAPSED_JOIN_CODE_RESERVE = `calc(${STAGE_AMBIENT_BAR_HEIGHT} - 0.5rem)`;

interface StageLayoutProps {
  songId: string;
  current?: KaraokeQueueItemWithSong | null;
  upcoming: KaraokeQueueItemWithSong[];
  onPlayFromQueue: (id: string) => void;
  onRemoveFromQueue: (id: string) => void;
  /**
   * Fullscreen, owned by the stage shell. The container it targets is the
   * shell's root, not this one, so the shell's other screens stay inside
   * full screen instead of disappearing with the browser chrome.
   */
  ui: PlayerUIHook;
  /** False while another stage screen is covering the player. */
  keyboardEnabled?: boolean;
}

const StageLayout: React.FC<StageLayoutProps> = ({
  songId,
  current,
  upcoming,
  onPlayFromQueue,
  onRemoveFromQueue,
  ui,
  keyboardEnabled = true,
}) => {
  const isPlaying = useKaraokePlayerStore((state) => state.isPlaying);
  const { collapsed } = useStageRails(isPlaying);
  const openSongSelect = useOpenSongSelect();
  const openLibrary = useCallback(() => openSongSelect(), [openSongSelect]);
  useStageKeyboard({
    onToggleFullscreen: ui.toggleFullscreen,
    onOpenLibrary: openLibrary,
    enabled: keyboardEnabled,
  });
  // keyboardEnabled is false exactly while another stage screen covers this one.
  useStageRootScale(keyboardEnabled);

  const nextItem = upcoming[0];
  const handleNext = useCallback(() => {
    if (nextItem) onPlayFromQueue(nextItem.id);
  }, [nextItem, onPlayFromQueue]);

  const railWidth = collapsed ? RAIL_COLLAPSED : RAIL_OPEN;
  // Hidden, not unmounted: `hidden` keeps React state, dialogs and drag
  // listeners alive while the rail is showing its icon strip.
  const railClass = cn(
    "flex min-h-0 flex-col transition-opacity duration-500",
    collapsed && "opacity-35",
  );

  return (
    <div
      tabIndex={-1}
      className="relative h-full w-full overflow-hidden outline-none"
    >
      {ui.fsError && (
        <div className="absolute right-3 top-3 z-40 rounded bg-destructive px-2 py-1 text-xs text-destructive-foreground shadow">
          {ui.fsError}
        </div>
      )}

      <div
        className="relative z-20 grid h-full gap-6 p-6 transition-[grid-template-columns] duration-500"
        style={{
          gridTemplateColumns: `${railWidth} minmax(0, 1fr) ${railWidth}`,
        }}
      >
        {/* Left rail — the same channel strip as the phone */}
        <div className={railClass}>
          <div className={cn(!collapsed && "hidden")}>
            <StageRailIcons side="left" />
          </div>
          <ControlsStrip
            density="tv"
            className={cn("flex-1", collapsed && "hidden")}
          />
        </div>

        {/* Centre — the player, with the transport under it */}
        <div className="flex min-h-0 flex-col items-center">
          {/* Autoplay: "Sing it now", the queue rail, Next and the handoff
            screen all mean "start this", so a new song counts in 3-2-1 and
            then plays by itself (useSongStart). The count waits while
            another screen covers the player. */}
          <KaraokePlayer
            songId={songId}
            autoPlay
            visible={keyboardEnabled}
            singer={current?.songId === songId ? current.singer : undefined}
            chromeCollapsed={collapsed}
          />
          {/* Fading alone would leave the lyrics stopping where the transport
            used to be. The 1fr -> 0fr row animates the height out too. */}
          <div
            className={cn(
              "grid w-full shrink-0 transition-[grid-template-rows,opacity,padding] duration-500",
              collapsed && "pointer-events-none opacity-0",
            )}
            style={{
              gridTemplateRows: collapsed ? "0fr" : "1fr",
              paddingBottom: collapsed ? COLLAPSED_TRANSPORT_RESERVE : 0,
            }}
          >
            {/* Clip only while collapsed, so the play button's glow isn't cut. */}
            <div className={cn("min-h-0", collapsed && "overflow-hidden")}>
              <StageTransport
                onNext={nextItem ? handleNext : undefined}
                onToggleFullscreen={ui.toggleFullscreen}
                isFullscreen={ui.isFullscreen}
              />
            </div>
          </div>
        </div>

        {/* Right rail — the queue, then the join code. The code sits outside
          the dimmed part so it stays scannable while the rail is collapsed. */}
        <div className="flex min-h-0 flex-col gap-4">
          <div className={cn(railClass, "flex-1")}>
            <div className={cn(!collapsed && "hidden")}>
              <StageRailIcons side="right" queueCount={upcoming.length} />
            </div>
            <div className={cn("min-h-0 flex-1", collapsed && "hidden")}>
              <StageQueueRail
                current={current}
                upcoming={upcoming}
                onPlay={onPlayFromQueue}
                onRemove={onRemoveFromQueue}
              />
            </div>
          </div>
          <StageJoinCode
            collapsed={collapsed}
            collapsedSize={COLLAPSED_JOIN_CODE_SIZE}
            collapsedInset={COLLAPSED_JOIN_CODE_RESERVE}
          />
        </div>
      </div>

      <StageAmbientBar visible={collapsed} />
    </div>
  );
};

export default StageLayout;
