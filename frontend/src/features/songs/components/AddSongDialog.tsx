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
import { createLogger } from "@/lib/logger";

const logger = createLogger("component:add-song");
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { LyricsResults } from "@/features/lyrics/components/LyricsResults";
import { MetadataEditForm, MetadataFormData } from "./MetadataEditForm";
import { useSongCreation } from "../hooks/useSongCreation";
import { useAddSongDialog } from "../hooks/useAddSongDialog";
import { useSaveMetadataMutation } from "@/hooks/api/useYoutube";
import type { CreateSongResponse } from "@/hooks/api/useYoutube";
import { Search, RotateCcw } from "lucide-react";
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

  // State for search refinement (lyrics only)
  const [refinedQuery, setRefinedQuery] = useState("");
  const [isRefining, setIsRefining] = useState(false);
  const [hasRefined, setHasRefined] = useState(false);

  // YouTube video flow specific state - metadata form
  const [editedMetadata, setEditedMetadata] = useState<MetadataFormData>({
    title: "",
    artist: "",
    album: "",
    genre: "",
  });

  // Save mutation for YouTube video flow
  const saveMetadataMutation = useSaveMetadataMutation(activeSong?.id || "", {
    onSuccess: () => {
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
      setRefinedQuery("");
      setIsRefining(false);
      setHasRefined(false);

      // Pre-populate search field with current song metadata when dialog opens
      if (currentSong) {
        const parts = [currentSong.artist, currentSong.title];
        if (currentSong.album) {
          parts.push(currentSong.album);
        }
        const defaultQuery = parts.join(" - ");
        setRefinedQuery(defaultQuery);
      }

      // Initialize metadata form for YouTube video flow
      if (flow === "youtube-video" && currentSong) {
        setEditedMetadata({
          title: videoTitle || currentSong.title || "",
          artist: currentSong.artist || "",
          album: currentSong.album || "",
          genre: "",
        });
      }
    }
  }, [isOpen, currentSong, flow, videoTitle]);

  const handleClose = () => {
    closeDialog();
    songCreation.resetState();
    setRefinedQuery("");
    setIsRefining(false);
    setHasRefined(false);
    setEditedMetadata({
      title: "",
      artist: "",
      album: "",
      genre: "",
    });
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

      await searchLyrics(customTitle, customArtist, currentSong.album);
    } catch (error) {
      logger.error("Failed to refine search:", error);
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
      await searchLyrics(
        currentSong.title,
        currentSong.artist,
        currentSong.album,
      );
    } catch (error) {
      logger.error("Failed to reset search:", error);
    } finally {
      setIsRefining(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && refinedQuery.trim()) {
      handleSearchRefinement();
    }
  };

  const handleYoutubeMusicConfirm = async () => {
    if (selectedLyrics) {
      try {
        await songCreation.saveLyrics(selectedLyrics);
      } catch (error) {
        logger.error("Failed to save lyrics:", error);
      }
    }
    handleClose();
  };

  const handleYoutubeVideoConfirm = async () => {
    if (!activeSong || !selectedLyrics) return;

    // Validate required fields
    if (!editedMetadata.title.trim() || !editedMetadata.artist.trim()) {
      toast.error("Title and Artist are required");
      return;
    }

    try {
      await saveMetadataMutation.mutateAsync({
        title: editedMetadata.title,
        artist: editedMetadata.artist,
        album: editedMetadata.album,
        primaryGenre: editedMetadata.primaryGenre,
        plainlyrics: selectedLyrics.plainLyrics,
        syncedLyrics: selectedLyrics.syncedLyrics,
      });
    } catch (error) {
      logger.error("Failed to save metadata and lyrics:", error);
    }
  };

  if (!currentSong || !activeSong) {
    return null;
  }

  const isYouTubeVideo = flow === "youtube-video";

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="sm:max-w-[700px] max-h-[90dvh] flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <DialogTitle>Add Song to Library</DialogTitle>
          <DialogDescription>
            Adding: <strong>{activeTitle}</strong>
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto">
          {isYouTubeVideo && (
            <>
              <MetadataEditForm
                initialTitle={editedMetadata.title}
                initialArtist={editedMetadata.artist}
                initialAlbum={editedMetadata.album}
                initialGenre={editedMetadata.primaryGenre}
                onChange={setEditedMetadata}
              />
              <Separator className="my-6" />
              <Label className="text-sm font-medium mb-3 block">
                Select Lyrics
              </Label>
            </>
          )}

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
        </div>

        {/* Search Refinement Section */}
        <div className="flex-shrink-0 pt-4 border-t space-y-3">
          <div className="space-y-2">
            <Label htmlFor="refine-search" className="text-sm font-medium">
              Refine lyrics search {hasRefined && "(using custom query)"}
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
                : "Not finding the right lyrics? Try searching with different terms like the exact song title or artist name."}
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end pt-4">
          <Button
            onClick={
              isYouTubeVideo
                ? handleYoutubeVideoConfirm
                : handleYoutubeMusicConfirm
            }
            disabled={
              !selectedLyrics ||
              (isYouTubeVideo &&
                (!editedMetadata.title.trim() || !editedMetadata.artist.trim()))
            }
          >
            {isYouTubeVideo ? "Confirm & Save" : "Confirm"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
