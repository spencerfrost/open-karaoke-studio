/**
 * SongSelectScreen - the stage's resting screen: pick something to sing.
 *
 * A song wheel rather than the phone's library. The phone's accordion of
 * artists is a web page; this screen is driven from across the room by a
 * mouse on the mic stand, or arrow keys, Enter and Back (see SongWheel). The
 * phone keeps LibraryScreen - the two share data hooks, not components.
 *
 * One slim bar at the top for the things that are not "pick a song": back to
 * the song that is playing, a quiet search for whoever has the keyboard, and
 * leaving stage mode - which the arrow keys can never reach, so nobody walking
 * up to sing ends the night by pressing Back one too many times. The join QR
 * code sits bottom-left rather than in the bar.
 */

import React, { useCallback, useMemo, useState } from "react";
import { LogOut, Plus, Search, Undo2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import SessionInfoDisplay from "@/components/session/SessionInfoDisplay";
import type { Song } from "@/types/Song";
import { useStageShell } from "../StageShellContext";
import StageSearch from "../components/StageSearch";
import SongWheel from "../wheel/SongWheel";
import type { WheelFocusRequest } from "../wheel/useSongWheel";

interface SongSelectScreenProps {
  /** Whether this is the screen showing. It stays mounted behind the others. */
  active: boolean;
  expandArtist?: string;
  /** Whether there is a song loaded to go back to. */
  hasCurrentSong: boolean;
  onExitStage: () => void;
}

const SongSelectScreen: React.FC<SongSelectScreenProps> = ({
  active,
  expandArtist,
  hasCurrentSong,
  onExitStage,
}) => {
  const shell = useStageShell();
  const [searching, setSearching] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  // Where the wheel should jump: the player's "more by this artist" (arriving
  // as a name on the screen state) or an artist picked from search. A new
  // object per request, so asking for the same artist twice still jumps.
  const [focusArtist, setFocusArtist] = useState<WheelFocusRequest | undefined>(
    () => (expandArtist ? { name: expandArtist } : undefined),
  );
  const [seenExpandArtist, setSeenExpandArtist] = useState(expandArtist);
  if (expandArtist !== seenExpandArtist) {
    setSeenExpandArtist(expandArtist);
    if (expandArtist) {
      setFocusArtist({ name: expandArtist });
      setSearching(false);
    }
  }

  const handlePickSong = useCallback(
    (song: Song) => shell?.openConfirm(song),
    [shell],
  );
  const handleLeave = useMemo(
    () => (hasCurrentSong ? () => shell?.openPerformance() : null),
    [hasCurrentSong, shell],
  );
  const handlePickArtist = useCallback((pick: WheelFocusRequest) => {
    setFocusArtist(pick);
    setSearching(false);
  }, []);
  const closeSearch = useCallback(() => setSearching(false), []);
  // State, not a ref: the wheel has to re-render once the layer exists.
  const [backdropEl, setBackdropEl] = useState<HTMLDivElement | null>(null);

  return (
    <div className="relative flex h-full w-full flex-col overflow-hidden">
      {/* The wheel's blurred backdrop, behind the whole screen. Everything
          after it is positioned, so it paints on top. */}
      <div ref={setBackdropEl} className="absolute inset-0" />

      <div className="relative flex shrink-0 items-center justify-between gap-4 px-6 pt-4">
        {hasCurrentSong ? (
          <Button
            variant="ghost"
            onClick={() => shell?.openPerformance()}
            className="text-foreground/60 hover:text-foreground"
          >
            <Undo2 className="mr-2 size-5" />
            Back to the song
          </Button>
        ) : (
          <span />
        )}

        <div className="flex items-center gap-2">
          {!searching && (
            <Button
              variant="ghost"
              onClick={() => setSearching(true)}
              className="text-foreground/50 hover:text-foreground"
            >
              <Search className="mr-2 size-5" />
              Search
            </Button>
          )}
          {/* Deliberately quiet: the mouse lives on the mic stand, and nobody
              walking up to sing should end the night by brushing this. */}
          <Button
            variant="ghost"
            size="sm"
            onClick={onExitStage}
            aria-label="Exit stage mode"
            className="text-foreground/35 hover:text-foreground"
          >
            <LogOut className="mr-2 size-4" />
            Exit stage
          </Button>
        </div>
      </div>

      <div className="relative min-h-0 flex-1">
        {/* The wheel stays mounted under search, keeping its place. */}
        <div className={searching ? "hidden" : "h-full"}>
          <SongWheel
            active={active && !searching}
            focusArtist={focusArtist}
            onPickSong={handlePickSong}
            onLeave={handleLeave}
            backdropTarget={backdropEl}
          />
        </div>
        {searching && active && (
          <div className="absolute inset-0">
            <StageSearch
              term={searchTerm}
              onTermChange={setSearchTerm}
              onPickArtist={handlePickArtist}
              onClose={closeSearch}
            />
          </div>
        )}
      </div>

      {/* Bottom-left, not in the top bar: at TV size the QR code made the bar
          ~150px tall, which the wheel had to shrink to fit under. This corner
          is empty beside the legend, and it is where guests look to join. */}
      <SessionInfoDisplay className="absolute bottom-6 left-6 z-10" />

      <Button
        variant="accent"
        size="lg"
        onClick={() => shell?.openAdd()}
        className="absolute bottom-8 right-8 z-10 size-16 rounded-full shadow-xl"
        aria-label="Add a song to the library"
      >
        <Plus className="size-8" />
      </Button>
    </div>
  );
};

/**
 * Memoized, and given only stable props by the shell. It stays mounted behind
 * the other screens, so the wheel keeps its place across a trip to confirm.
 */
export default React.memo(SongSelectScreen);
