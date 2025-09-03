import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MetadataResults } from "@/components/MetadataResults";
import { LyricsResults } from "@/components/LyricsResults";
import { useSongCreation } from "@/hooks/useSongCreation";
import { useAddSongDialog } from "@/hooks/useAddSongDialog";
import { useMetadata } from "@/hooks/api/useMetadata";
import { useSaveMetadataMutation } from "@/hooks/api/useYoutube";
import type { MetadataOption } from "@/hooks/api/useMetadata";
import type { CreateSongResponse } from "@/hooks/api/useYoutube";
import { Search, RotateCcw, ChevronLeft, ChevronRight } from "lucide-react";
import { toast } from "sonner";

interface AddSongDialogContainerProps {
  songCreation: ReturnType<typeof useSongCreation>;
  dialog: ReturnType<typeof useAddSongDialog>;
  flow?: "youtube-music" | "youtube-video";
  // Additional props for YouTube video flow
  videoTitle?: string;
  videoDuration?: number;
  createdSong?: CreateSongResponse;
  onComplete?: () => void;
}

export const AddSongDialog: React.FC<AddSongDialogContainerProps> = ({
  songCreation,
  dialog,
  flow = "youtube-music",
  videoTitle,
  videoDuration,
  createdSong,
  onComplete,
}) => {
  const {
    currentSong,
    createdSong: songCreationCreatedSong,
    lyricsOptions,
    isLoadingLyrics,
    searchLyrics,
  } = songCreation;
  const { isOpen, selectedLyrics, closeDialog, selectLyrics } = dialog;

  // Use the appropriate created song and metadata based on flow
  const activeSong =
    flow === "youtube-video" ? createdSong : songCreationCreatedSong;
  const activeTitle =
    flow === "youtube-video" ? videoTitle : currentSong?.title;
  const activeDuration =
    flow === "youtube-video" ? videoDuration : currentSong?.duration;

  // Page navigation for YouTube video flow (lyrics -> metadata)
  const [currentPage, setCurrentPage] = useState<"lyrics" | "metadata">(
    "lyrics",
  );

  // State for search refinement
  const [refinedQuery, setRefinedQuery] = useState("");
  const [isRefining, setIsRefining] = useState(false);
  const [hasRefined, setHasRefined] = useState(false);

  // YouTube video flow specific state
  const [selectedMetadata, setSelectedMetadata] =
    useState<MetadataOption | null>(null);

  // Metadata search for YouTube video flow
  const { useSearchMetadata } = useMetadata();
  const searchMetadata = useSearchMetadata();
  const metadataOptions = searchMetadata.data?.results || [];

  // Save mutation for YouTube video flow
  const saveMetadataMutation = useSaveMetadataMutation(activeSong?.id || "", {
    onSuccess: () => {
      toast.success("Song added to library successfully!");
      onComplete?.();
      handleClose();
    },
    onError: (error) => {
      toast.error(`Failed to save metadata: ${error.message}`);
    },
  });

  // Reset state when dialog opens
  useEffect(() => {
    if (isOpen) {
      setCurrentPage("lyrics");
      setRefinedQuery("");
      setIsRefining(false);
      setHasRefined(false);
      setSelectedMetadata(null);

      // Pre-populate search field with current song metadata when dialog opens
      if (currentSong) {
        const parts = [currentSong.artist, currentSong.title];
        if (currentSong.album) {
          parts.push(currentSong.album);
        }
        const defaultQuery = parts.join(" - ");
        setRefinedQuery(defaultQuery);
      }

      // For YouTube video flow, immediately start metadata search
      if (flow === "youtube-video" && currentSong) {
        setTimeout(() => {
          searchMetadata.mutate({
            artist: currentSong.artist,
            title: currentSong.title,
            album: currentSong.album,
          });
        }, 100);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, currentSong, flow]);

  const handleClose = () => {
    closeDialog();
    songCreation.resetState();
    setCurrentPage("lyrics");
    setRefinedQuery("");
    setIsRefining(false);
    setHasRefined(false);
    setSelectedMetadata(null);
  };

  const handleSearchRefinement = async () => {
    if (!refinedQuery.trim() || !currentSong) return;

    setIsRefining(true);
    setHasRefined(true);

    try {
      // Parse the refined query to extract potential artist and title
      let customTitle = refinedQuery.trim();
      let customArtist = currentSong.artist;

      // Simple heuristic: if query contains " - " or " by ", try to split artist and title
      if (refinedQuery.includes(" - ")) {
        const [artist, title] = refinedQuery.split(" - ", 2);
        if (artist.trim() && title.trim()) {
          customArtist = artist.trim();
          customTitle = title.trim();
        }
      } else if (refinedQuery.includes(" by ")) {
        const [title, artist] = refinedQuery.split(" by ", 2);
        if (artist.trim() && title.trim()) {
          customArtist = artist.trim();
          customTitle = title.trim();
        }
      }

      if (currentPage === "lyrics") {
        await searchLyrics(customTitle, customArtist, currentSong.album);
      } else if (currentPage === "metadata") {
        searchMetadata.mutate({
          artist: customArtist,
          title: customTitle,
          album: currentSong.album,
        });
      }
    } catch (error) {
      console.error("Failed to refine search:", error);
    } finally {
      setIsRefining(false);
    }
  };

  const handleResetSearch = async () => {
    if (!currentSong) return;

    setIsRefining(true);
    setRefinedQuery("");
    setHasRefined(false);

    try {
      // Reset to original search using original song metadata
      if (currentPage === "lyrics") {
        await searchLyrics(
          currentSong.title,
          currentSong.artist,
          currentSong.album,
        );
      } else if (currentPage === "metadata") {
        searchMetadata.mutate({
          artist: currentSong.artist,
          title: currentSong.title,
          album: currentSong.album,
        });
      }
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

  // Handle page navigation for YouTube video flow
  const handleLyricsNext = () => {
    if (flow === "youtube-video") {
      setCurrentPage("metadata");
    } else {
      handleYoutubeMusicConfirm();
    }
  };

  const handleMetadataConfirm = () => {
    saveMetadataMutation.mutate({
      title: selectedMetadata?.title || currentSong?.title || "",
      artist: selectedMetadata?.artist || currentSong?.artist || "",
      album: selectedMetadata?.album || currentSong?.album || "",
      plainlyrics: selectedLyrics?.plainLyrics,
      syncedLyrics: selectedLyrics?.syncedLyrics,
      metadataId: selectedMetadata?.metadataId,
    });
  };

  const handleYoutubeMusicConfirm = async () => {
    if (selectedLyrics) {
      try {
        await songCreation.saveLyrics(selectedLyrics);
      } catch (error) {
        console.error("Failed to save lyrics:", error);
      }
    }
    handleClose();
  };

  if (!currentSong || !activeSong) {
    return null;
  }

  const isLyricsPage = currentPage === "lyrics";
  const isMetadataPage = currentPage === "metadata";
  const isYouTubeVideo = flow === "youtube-video";

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="sm:max-w-[700px] max-h-[90dvh] flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <DialogTitle>Add Song to Library</DialogTitle>
          <DialogDescription>
            Adding: <strong>{activeTitle}</strong>
            {isYouTubeVideo && (
              <span className="ml-2 text-xs text-muted-foreground">
                Step {currentPage === "lyrics" ? "1" : "2"} of 2
              </span>
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto">
          {isLyricsPage && (
            <LyricsResults
              isLoading={isLoadingLyrics || isRefining}
              options={lyricsOptions || []}
              selectedOption={selectedLyrics}
              onSelectionChange={selectLyrics}
              {...(flow === "youtube-video"
                ? { youtubeDurationSeconds: Number(activeDuration) || 0 }
                : {
                    youtubeMusicDurationSeconds:
                      activeDuration?.toString() || "0",
                  })}
            />
          )}

          {isMetadataPage && isYouTubeVideo && (
            <MetadataResults
              isLoading={searchMetadata.isPending || isRefining}
              options={metadataOptions}
              selectedOption={selectedMetadata}
              onSelectionChange={setSelectedMetadata}
              autoSelectFirst={true}
              emptyMessage="No metadata found for this search"
            />
          )}
        </div>

        {/* Search Refinement Section */}
        <div className="flex-shrink-0 pt-4 border-t space-y-3">
          <div className="space-y-2">
            <Label htmlFor="refine-search" className="text-sm font-medium">
              Refine {currentPage} search {hasRefined && "(using custom query)"}
            </Label>
            <div className="flex gap-2">
              <Input
                id="refine-search"
                placeholder="Enter search terms (e.g., 'Artist - Title' or 'Title by Artist')"
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
                : `Not finding the right ${currentPage}? Try searching with different terms like the exact song title or artist name.`}
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-between pt-4">
          <div>
            {isYouTubeVideo && isMetadataPage && (
              <Button
                onClick={() => setCurrentPage("lyrics")}
                variant="outline"
                size="sm"
              >
                <ChevronLeft className="h-4 w-4 mr-1" />
                Back to Lyrics
              </Button>
            )}
          </div>

          <div className="flex gap-2">
            {isYouTubeVideo && isMetadataPage && (
              <Button onClick={handleMetadataConfirm} variant="outline">
                Skip Metadata
              </Button>
            )}

            <Button
              onClick={isLyricsPage ? handleLyricsNext : handleMetadataConfirm}
              disabled={isLyricsPage ? !selectedLyrics : false}
            >
              {isLyricsPage ? (
                isYouTubeVideo ? (
                  <>
                    Next: Metadata <ChevronRight className="h-4 w-4 ml-1" />
                  </>
                ) : (
                  "Confirm"
                )
              ) : (
                "Confirm"
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
