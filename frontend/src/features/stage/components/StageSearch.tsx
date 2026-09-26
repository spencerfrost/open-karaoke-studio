/**
 * StageSearch - typing, for whoever has the keyboard from the coffee table.
 *
 * The wheel reaches every song without typing; this is the shortcut beside
 * it. Songs render as the library's usual cards, which already route through
 * the stage's confirm screen. Matching artists are buttons that hand back to
 * the wheel, landed on that artist - search to get close, the wheel to browse.
 */

import React, { useEffect, useRef, useState } from "react";
import { Plus, Theater } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useArtists } from "@/hooks/api/useArtists";
import { useSongs } from "@/hooks/api/useSongs";
import LibrarySearchInput from "@/features/library/components/LibrarySearchInput";
import SongResultsSection from "@/features/library/components/SongResultsSection";
import type { Song } from "@/types/Song";
import { useStageShell } from "../StageShellContext";
import type { WheelFocusRequest } from "../wheel/useSongWheel";

/** Artists shown above the songs; past this the song results matter more. */
const MAX_ARTISTS = 12;

interface StageSearchProps {
  /** The search term, owned by the caller so it survives a trip to confirm. */
  term: string;
  onTermChange: (term: string) => void;
  onPickArtist: (artist: WheelFocusRequest) => void;
  onClose: () => void;
}

const StageSearch: React.FC<StageSearchProps> = ({
  term,
  onTermChange,
  onPickArtist,
  onClose,
}) => {
  const shell = useStageShell();
  const inputWrapRef = useRef<HTMLDivElement>(null);
  const [inputFocused, setInputFocused] = useState(false);

  // Straight into the field: whoever opened search is holding a keyboard.
  useEffect(() => {
    inputWrapRef.current?.querySelector("input")?.focus();
  }, []);

  // Escape leaves search from the field. Backspace does too once the field is
  // not focused, so the wheel's Back key still works here.
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const t = e.target instanceof HTMLElement ? e.target : null;
      if (t?.closest("[role='dialog']")) return;
      const inField = t?.tagName === "INPUT";
      if (e.key === "Escape" || (e.key === "Backspace" && !inField)) {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const trimmed = term.trim();
  const { useSongs: useSongsQuery } = useSongs();
  const songsQuery = useSongsQuery(
    { q: trimmed, limit: 24, offset: 0, sort: "relevance", direction: "desc" },
    { enabled: trimmed.length > 0 },
  );
  const { artists } = useArtists({ search: trimmed });
  const songs: Song[] = trimmed ? (songsQuery.data ?? []) : [];
  const matchedArtists = trimmed ? artists.slice(0, MAX_ARTISTS) : [];
  const nothingFound =
    trimmed.length > 0 &&
    !songsQuery.isLoading &&
    songs.length === 0 &&
    matchedArtists.length === 0;

  return (
    <div className="flex h-full w-full flex-col overflow-hidden">
      <div
        ref={inputWrapRef}
        className="mx-auto w-full max-w-2xl shrink-0 px-6 pb-6 pt-2"
        onFocus={() => setInputFocused(true)}
        onBlur={() => setInputFocused(false)}
      >
        <LibrarySearchInput
          searchTerm={term}
          onSearchChange={onTermChange}
          isLoading={songsQuery.isLoading && trimmed.length > 0}
          placeholder="What do you want to sing?"
          debounceMs={300}
        />
        <p className="pt-2 text-center text-sm text-foreground/40">
          {inputFocused ? "Esc" : "Esc or ⌫"} to go back to the wheel
        </p>
      </div>

      <div className="min-h-0 flex-1 overflow-auto px-6 pb-24">
        {matchedArtists.length > 0 && (
          <div className="mb-8 flex flex-wrap gap-3">
            {matchedArtists.map((artist) => (
              <Button
                key={`${artist.isShow ? "show" : "artist"}:${artist.name}`}
                variant="outline"
                size="lg"
                onClick={() =>
                  onPickArtist({ name: artist.name, isShow: artist.isShow })
                }
                className="rounded-full text-lg"
              >
                {artist.isShow && <Theater className="mr-2 size-4" />}
                {artist.name}
                <span className="ml-2 text-foreground/40">
                  {artist.songCount}
                </span>
              </Button>
            ))}
          </div>
        )}

        {songs.length > 0 && (
          <SongResultsSection
            songs={songs}
            hasNextPage={false}
            isFetchingNextPage={false}
            fetchNextPage={() => {}}
            searchTerm={trimmed}
          />
        )}

        {nothingFound && (
          <div className="flex flex-col items-center gap-4 pt-12 text-xl text-foreground/60">
            Nothing in the library matches "{trimmed}".
            <Button
              variant="accent"
              size="lg"
              onClick={() => shell?.openAdd({ query: trimmed })}
            >
              <Plus className="mr-2 size-5" />
              Find it online
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};

export default StageSearch;
