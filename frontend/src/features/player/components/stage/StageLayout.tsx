/**
 * StageLayout - the stage itself: three columns filling the viewport.
 *
 * Left rail is the same ControlsStrip the phone renders; the centre column is
 * the player; the right rail is the queue. The transport sits under the centre
 * column only, so the rails keep the full height.
 *
 * While a song plays the rails collapse to icon strips and the chrome dims —
 * but nothing unmounts, so dialogs, drag state and focus all survive.
 *
 * The backdrop (sunburst, texture, scrim) belongs to the shell, not here: it is
 * shared with every other stage screen, and painting a second full-viewport
 * copy of it per screen is expensive enough to be felt on every click.
 */

import React, { useCallback } from "react";
import { ControlsStrip } from "@/features/performance/controls";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { cn } from "@/lib/utils";
import type { PlayerUIHook } from "../../types/KaraokePlayer.types";
import KaraokePlayer from "../KaraokePlayer";
import StageTransport from "./StageTransport";
import StageAmbientBar from "./StageAmbientBar";
import StageQueueRail from "./StageQueueRail";
import StageRailIcons from "./StageRailIcons";
import { useStageRails } from "./useStageRails";
import { useStageKeyboard } from "./useStageKeyboard";
import type { KaraokeQueueItemWithSong } from "@/types/KaraokeQueue";

const RAIL_OPEN_PX = 356;
const RAIL_COLLAPSED_PX = 96;

interface StageLayoutProps {
  songId: string;
  current?: KaraokeQueueItemWithSong | null;
  upcoming: KaraokeQueueItemWithSong[];
  queueItems?: KaraokeQueueItemWithSong[];
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
  queueItems,
  onPlayFromQueue,
  onRemoveFromQueue,
  ui,
  keyboardEnabled = true,
}) => {
  const isPlaying = useKaraokePlayerStore((state) => state.isPlaying);
  const { collapsed } = useStageRails(isPlaying);
  useStageKeyboard({
    onToggleFullscreen: ui.toggleFullscreen,
    enabled: keyboardEnabled,
  });

  const nextItem = upcoming[0];
  const handleNext = useCallback(() => {
    if (nextItem) onPlayFromQueue(nextItem.id);
  }, [nextItem, onPlayFromQueue]);

  const railWidth = collapsed ? RAIL_COLLAPSED_PX : RAIL_OPEN_PX;
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
          gridTemplateColumns: `${railWidth}px minmax(0, 1fr) ${railWidth}px`,
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
          <KaraokePlayer
            songId={songId}
            queueItems={queueItems}
            onPlayNext={onPlayFromQueue}
            dimHeader={collapsed}
          />
          <div
            className={cn(
              "w-full shrink-0 transition-opacity duration-500",
              collapsed && "pointer-events-none opacity-0",
            )}
          >
            <StageTransport
              onNext={nextItem ? handleNext : undefined}
              onToggleFullscreen={ui.toggleFullscreen}
              isFullscreen={ui.isFullscreen}
            />
          </div>
        </div>

        {/* Right rail — the queue */}
        <div className={railClass}>
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
      </div>

      <StageAmbientBar visible={collapsed} />
    </div>
  );
};

export default StageLayout;
