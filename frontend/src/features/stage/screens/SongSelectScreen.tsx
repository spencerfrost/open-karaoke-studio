/**
 * SongSelectScreen - the stage's resting screen: pick something to sing.
 *
 * A song wheel rather than the phone's library. The phone's accordion of
 * artists is a web page; this screen is driven from across the room by a
 * mouse on the mic stand, or arrow keys, Enter and Back (see SongWheel). The
 * phone keeps LibraryScreen - the two share data hooks, not components.
 *
 * One slim bar at the top for the things that are not "pick a song": adding a
 * song (also a row of the wheel's first column, for the arrow keys; up here
 * it is always on screen for the mouse), a quiet search for whoever has the
 * keyboard, and leaving stage mode - which the arrow keys can never reach, so
 * nobody walking up to sing ends the night by pressing Back one too many
 * times. The join QR code sits bottom-right, where the performance screen has
 * it, rather than in the bar. The now-playing footer, which is also the way
 * back to the song, runs along the bottom.
 */

import React, { useCallback, useMemo, useState } from "react";
import { LogOut, Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import SessionInfoDisplay from "@/components/session/SessionInfoDisplay";
import { browseArtistOptions } from "@/hooks/useOpenAddSong";
import type { Song } from "@/types/Song";
import { useStageShell } from "../StageShellContext";
import StageNowPlaying from "../components/StageNowPlaying";
import StageProcessingList from "../components/StageProcessingList";
import StageSearch from "../components/StageSearch";
import SongWheel from "../wheel/SongWheel";
import type { WheelFocusRequest } from "../wheel/useSongWheel";
import type { WheelArtist } from "../wheel/wheelModel";

interface SongSelectScreenProps {
  /** Whether this is the screen showing. It stays mounted behind the others. */
  active: boolean;
  expandArtist?: string;
  /** Whether there is a song loaded to go back to. The wheel's Back needs it. */
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
  // The shell decides where leaving goes: the song, or the handoff screen once
  // it has ended.
  const handleLeave = useMemo(
    () => (hasCurrentSong ? () => shell?.back() : null),
    [hasCurrentSong, shell],
  );
  const handlePickArtist = useCallback((pick: WheelFocusRequest) => {
    setFocusArtist(pick);
    setSearching(false);
  }, []);
  const closeSearch = useCallback(() => setSearching(false), []);
  const handleAddSong = useCallback(() => shell?.openAdd(), [shell]);
  const handleFindMore = useCallback(
    (artist: WheelArtist) => shell?.openAdd(browseArtistOptions(artist)),
    [shell],
  );
  // State, not a ref: the wheel has to re-render once the layer exists.
  const [backdropEl, setBackdropEl] = useState<HTMLDivElement | null>(null);

  return (
    <div className="relative flex h-full w-full flex-col overflow-hidden">
      {/* The wheel's blurred backdrop, behind the whole screen. Everything
          after it is positioned, so it paints on top. */}
      <div ref={setBackdropEl} className="absolute inset-0" />

      <div className="relative flex shrink-0 items-center justify-end gap-4 px-6 pt-4">
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            onClick={handleAddSong}
            className="text-foreground-faint hover:text-foreground"
          >
            <Plus className="mr-2 size-5" />
            Add a song
          </Button>
          {!searching && (
            <Button
              variant="ghost"
              onClick={() => setSearching(true)}
              className="text-foreground-faint hover:text-foreground"
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
            className="text-foreground-faint hover:text-foreground"
          >
            <LogOut className="mr-2 size-4" />
            Exit stage
          </Button>
        </div>
      </div>

      <div className="relative flex min-h-0 flex-1">
        {/* The songs that guests who just joined are adding, in a column of
            their own: the wheel is scaled to fit, so it shrinks to make room
            instead of being covered. On a computer the wheel is limited by
            height and doesn't shrink at all. The column collapses when
            nothing is processing, and while searching, which covers the wheel.
            Wide enough on a computer for the tour's card to sit under it. */}
        <aside className="relative z-10 w-64 shrink-0 pl-4 pt-2 empty:hidden xl:w-96 xl:pl-6">
          {!searching && <StageProcessingList className="w-full" />}
        </aside>

        <div className="relative min-w-0 flex-1">
          {/* The wheel stays mounted under search, keeping its place. */}
          <div className={searching ? "hidden" : "h-full"}>
            <SongWheel
              active={active && !searching}
              focusArtist={focusArtist}
              onPickSong={handlePickSong}
              onAddSong={handleAddSong}
              onFindMore={handleFindMore}
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

        {/* Inside the wheel area, so it sits above the footer. Bottom-right,
            not in the top bar: at TV size the QR code made the bar ~150px
            tall, which the wheel had to shrink to fit under. This corner is
            empty beside the legend, and it is where the performance screen
            keeps its code, so guests look for it in one place. */}
        <SessionInfoDisplay className="absolute bottom-6 right-6 z-10" />
      </div>

      {/* Reads the store and the shell's queue itself, so the playing song
          never re-renders this memoized screen. */}
      <StageNowPlaying />
    </div>
  );
};

/**
 * Memoized, and given only stable props by the shell. It stays mounted behind
 * the other screens, so the wheel keeps its place across a trip to confirm.
 */
export default React.memo(SongSelectScreen);
