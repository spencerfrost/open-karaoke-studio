import React, { useState, useEffect } from "react";
import { Song } from "@/types/Song";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Search, RotateCcw } from "lucide-react";
import { LyricsResults } from "@/components/LyricsResults";
import { useLyricsSearch } from "@/hooks/api/useLyrics";
import type { LyricsOption } from "@/hooks/api/useLyrics";

export interface LyricsResult {
  id?: string;
  plainLyrics?: string;
  syncedLyrics?: string;
  trackName?: string;
  artistName?: string;
  albumName?: string;
  duration?: number;
  source?: string;
}

export interface LyricsFetchDialogProps {
  /** Whether the dialog is open */
  isOpen: boolean;
  /** Function to close the dialog */
  onClose: () => void;
  /** Song to search lyrics for */
  song?: Song | null;
  /** Callback when a specific lyrics result is selected */
  onLyricsSelected?: (lyrics: LyricsResult) => void;
}

export const LyricsFetchDialog: React.FC<LyricsFetchDialogProps> = ({
  isOpen,
  onClose,
  song,
  onLyricsSelected,
}) => {
  // State for search refinement
  const [refinedQuery, setRefinedQuery] = useState("");
  const [isRefining, setIsRefining] = useState(false);
  const [hasRefined, setHasRefined] = useState(false);
  const [selectedLyrics, setSelectedLyrics] = useState<LyricsOption | null>(null);

  // Lyrics search hook
  const lyricsSearch = useLyricsSearch();
  const lyricsOptions = lyricsSearch.data || [];
  const isLoadingLyrics = lyricsSearch.loading;

  // Reset state when dialog opens
  useEffect(() => {
    if (isOpen && song) {
      setRefinedQuery("");
      setIsRefining(false);
      setHasRefined(false);
      setSelectedLyrics(null);

      // Pre-populate search field with song metadata when dialog opens
      const parts = [song.artist, song.title];
      if (song.album) {
        parts.push(song.album);
      }
      const defaultQuery = parts.join(" - ");
      setRefinedQuery(defaultQuery);

      // Immediately start lyrics search
      setTimeout(() => {
        lyricsSearch.search({
          artist: song.artist,
          title: song.title,
          album: song.album,
        });
      }, 100);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, song]);

  const handleClose = () => {
    onClose();
    setRefinedQuery("");
    setIsRefining(false);
    setHasRefined(false);
    setSelectedLyrics(null);
  };

  const handleSearchRefinement = async () => {
    if (!refinedQuery.trim() || !song) return;

    setIsRefining(true);
    setHasRefined(true);

    try {
      // Parse the refined query - assume format is "artist - title - album" or "artist - title"
      const parts = refinedQuery.split(" - ").map(part => part.trim());
      const artist = parts[0] || song.artist;
      const title = parts[1] || song.title;
      const album = parts[2] || song.album;

      await lyricsSearch.search({
        artist,
        title,
        album,
      });
    } catch (error) {
      console.error("Failed to refine search:", error);
    } finally {
      setIsRefining(false);
    }
  };

  const handleResetSearch = async () => {
    if (!song) return;

    setIsRefining(true);
    setHasRefined(false);

    try {
      // Reset to original song metadata
      const parts = [song.artist, song.title];
      if (song.album) {
        parts.push(song.album);
      }
      setRefinedQuery(parts.join(" - "));

      // Search with original metadata
      await lyricsSearch.search({
        artist: song.artist,
        title: song.title,
        album: song.album,
      });
    } catch (error) {
      console.error("Failed to reset search:", error);
    } finally {
      setIsRefining(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && refinedQuery.trim()) {
      handleSearchRefinement();
    }
  };

  const handleLyricsConfirm = () => {
    if (selectedLyrics && onLyricsSelected) {
      // Convert LyricsOption to LyricsResult format
      const lyricsResult: LyricsResult = {
        id: selectedLyrics.id,
        plainLyrics: selectedLyrics.plainLyrics,
        syncedLyrics: selectedLyrics.syncedLyrics,
        trackName: selectedLyrics.trackName,
        artistName: selectedLyrics.artistName,
        albumName: selectedLyrics.albumName,
        duration: selectedLyrics.duration,
        source: selectedLyrics.source,
      };
      onLyricsSelected(lyricsResult);
    }
    handleClose();
  };

  if (!song) {
    return null;
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="sm:max-w-[700px] max-h-[90dvh] flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <DialogTitle>Search for Lyrics</DialogTitle>
          <DialogDescription>
            Finding lyrics for: <strong>{song.title}</strong> by <strong>{song.artist}</strong>
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto">
          <LyricsResults
            isLoading={isLoadingLyrics || isRefining}
            options={lyricsOptions}
            selectedOption={selectedLyrics}
            onSelectionChange={setSelectedLyrics}
            duration={song.duration || 0}
          />
        </div>

        {/* Search Refinement */}
        <div className="border-t pt-4 flex-shrink-0">
          <div className="space-y-2">
            <div className="flex gap-2">
              <Input
                id="refine-search"
                placeholder="Enter search terms (e.g., 'Artist - Title - Album')"
                value={refinedQuery}
                onChange={(e) => setRefinedQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isRefining}
                className="flex-1"
              />
              <Button
                onClick={handleSearchRefinement}
                disabled={!refinedQuery.trim() || isRefining}
                size="sm"
                variant="outline"
              >
                <Search className="h-4 w-4" />
              </Button>
              {hasRefined && (
                <Button
                  onClick={handleResetSearch}
                  disabled={isRefining}
                  size="sm"
                  variant="outline"
                  title="Reset to original search"
                >
                  <RotateCcw className="h-4 w-4" />
                </Button>
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              {hasRefined
                ? "You're viewing results for a custom search. Click reset to return to the original search."
                : "Not finding the right lyrics? Try searching with different terms like the exact song title or artist name."}
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-between pt-4 border-t">
          <div></div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleClose}>
              Cancel
            </Button>
            <Button
              onClick={handleLyricsConfirm}
              disabled={!selectedLyrics}
            >
              Use Selected Lyrics
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default LyricsFetchDialog;
