// frontend/src/components/upload/YouTubeSearch.tsx
import React, { useState } from "react";
import { Loader2, Search } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { MetadataDialog } from "./MetadataDialog";
import { VerificationDialog } from "./VerificationDialog";
import {
  useYoutubeDownloadMutation,
  useLyricsSearch,
  useMetadataSearch,
  useSaveMetadataMutation,
  useCreateSongMutation, // Add this import
  LyricsOption,
  MetadataOption,
  CreateSongResponse,
} from "@/hooks/useYoutube";

// Helper functions
const formatDuration = (seconds: number) => {
  if (!seconds) return "0:00";
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
};

export interface YouTubeSearchResult {
  id: string;
  title: string;
  uploader: string;
  duration: number;
  thumbnail: string;
  url: string;
}

const YouTubeSearch: React.FC = () => {
  // Search form state
  const [artistInput, setArtistInput] = useState("");
  const [titleInput, setTitleInput] = useState("");
  const [albumInput, setAlbumInput] = useState("");

  const [results, setResults] = useState<YouTubeSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchPerformed, setSearchPerformed] = useState(false);
  const [downloadingIds, setDownloadingIds] = useState<string[]>([]);
  const [selectedResult, setSelectedResult] =
    useState<YouTubeSearchResult | null>(null);
  // Dialog states
  const [isMetadataDialogOpen, setIsMetadataDialogOpen] = useState(false);
  const [isVerificationDialogOpen, setIsVerificationDialogOpen] =
    useState(false);

  // Confirmed metadata from first dialog
  const [confirmedMetadata, setConfirmedMetadata] = useState<{
    title: string;
    artist: string;
    album: string;
  }>({ title: "", artist: "", album: "" });
  const [createdSong, setCreatedSong] = useState<CreateSongResponse | null>(
    null
  );

  // --- API Hooks ---
  const createSongMutation = useCreateSongMutation({
    onSuccess: (data) => {
      console.log("Song created in database:", data);
      setCreatedSong(data);

      // After song creation, start YouTube download with the song ID
      if (selectedResult) {
        youtubeDownloadMutation.mutate({
          videoId: selectedResult.id,
          title: data.title,
          artist: data.artist,
          album: data.album,
          songId: data.id,
        });
      }

      // Show metadata confirmation dialog
      setConfirmedMetadata({
        title: data.title,
        artist: data.artist,
        album: data.album || "",
      });
      setIsMetadataDialogOpen(true);
    },
    onError: (error) => {
      toast.error(`Failed to create song: ${error.message}`);
      if (selectedResult) {
        setDownloadingIds((prev) =>
          prev.filter((id) => id !== selectedResult.id)
        );
        setSelectedResult(null);
      }
    },
  });

  const youtubeDownloadMutation = useYoutubeDownloadMutation({
    onSuccess: () => {
      toast.success("YouTube download started in background");
    },
    onError: (error) => {
      toast.error(`Failed to start download: ${error.message}`);
      if (selectedResult) {
        setDownloadingIds((prev) =>
          prev.filter((id) => id !== selectedResult.id)
        );
      }
    },
  });

  // Initialize the queries with enabled: false so they don't run immediately
  const {
    data: lyricsOptions = [],
    refetch: fetchLyrics,
    isPending: isLoadingLyrics,
  } = useLyricsSearch(
    {
      title: confirmedMetadata.title,
      artist: confirmedMetadata.artist,
      album: confirmedMetadata.album,
    },
    {
      enabled: false,
      queryKey: ["lyrics", confirmedMetadata.artist, confirmedMetadata.title],
    }
  );

  const {
    data: metadataOptions = [],
    refetch: fetchMetadata,
    isPending: isLoadingMetadata,
  } = useMetadataSearch(
    {
      title: confirmedMetadata.title,
      artist: confirmedMetadata.artist,
    },
    {
      enabled: false,
      queryKey: ["metadata", confirmedMetadata.artist, confirmedMetadata.title],
    }
  );

  const saveMetadataMutation = useSaveMetadataMutation(
    createdSong?.id || "dummy",
    {
      onSuccess: () => {
        toast.success(
          "Song added to library with selected metadata and lyrics"
        );
        setIsVerificationDialogOpen(false);

        if (selectedResult) {
          setDownloadingIds((prev) =>
            prev.filter((id) => id !== selectedResult.id)
          );
          setSelectedResult(null);
        }
      },
      onError: (error) => {
        toast.error(`Failed to save metadata: ${error.message}`);
      },
    }
  );

  // --- Event Handlers ---
  const handleSearch = async () => {
    if (!artistInput.trim() || !titleInput.trim()) {
      toast.error("Please enter both artist and title");
      return;
    }

    const searchQuery = `${artistInput} ${titleInput}`;
    setIsSearching(true);

    try {
      const response = await fetch(
        `/api/youtube/search?query=${encodeURIComponent(searchQuery)}`
      );
      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      setResults(data.data || []);
      setSearchPerformed(true);
    } catch (error) {
      toast.error(
        `Search failed: ${error instanceof Error ? error.message : "Unknown error"}`
      );
    } finally {
      setIsSearching(false);
    }
  };

  const handleSelectVideo = (result: YouTubeSearchResult) => {
    setSelectedResult(result);
    setDownloadingIds((prev) => [...prev, result.id]);

    // Step 1: Create a song record in the database first
    createSongMutation.mutate({
      title: titleInput,
      artist: artistInput,
      album: albumInput,
      source: "youtube",
      sourceUrl: result.url,
      videoId: result.id,
      videoTitle: result.title,
    });

    // Step 2: YouTube download is now triggered in the onSuccess callback of createSongMutation

    // Step 3: Metadata confirmation dialog is also shown in the onSuccess callback
  };

  const handleMetadataConfirm = (metadata: {
    artist: string;
    title: string;
    album: string;
  }) => {
    setConfirmedMetadata(metadata);
    setIsMetadataDialogOpen(false);

    // Step 3: Fetch lyrics and metadata options with confirmed data
    fetchLyrics();
    fetchMetadata();

    // Open verification dialog after both are fetched
    setTimeout(() => {
      setIsVerificationDialogOpen(true);
    }, 500); // Small delay to allow both to fetch
  };

  // Update the saveMetadataMutation to use the created song ID
  const handleVerificationSubmit = (selections: {
    selectedLyrics: LyricsOption | null;
    selectedMetadata: MetadataOption | null;
  }) => {
    if (!createdSong) return;

    // Step 4: Save final selections using the created song ID
    saveMetadataMutation.mutate({
      title: selections.selectedMetadata?.title || confirmedMetadata.title,
      artist: selections.selectedMetadata?.artist || confirmedMetadata.artist,
      album: selections.selectedMetadata?.album || confirmedMetadata.album,
      lyrics: selections.selectedLyrics?.plainLyrics,
      syncedLyrics: selections.selectedLyrics?.syncedLyrics,
      musicbrainzId: selections.selectedMetadata?.musicbrainzId,
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Search YouTube</CardTitle>
        <CardDescription>
          Enter song details to find and add to your karaoke library
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="w-full">
          {/* Search Form */}
          <div className="flex flex-col gap-3 mb-6">
            <div className="flex flex-col md:flex-row gap-2">
              <div className="flex-1">
                <Label htmlFor="artist" className="mb-1 block text-sm">
                  Artist
                </Label>
                <Input
                  id="artist"
                  placeholder="Enter artist name"
                  value={artistInput}
                  onChange={(e) => setArtistInput(e.target.value)}
                  className="w-full"
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                />
              </div>
              <div className="flex-1">
                <Label htmlFor="title" className="mb-1 block text-sm">
                  Title
                </Label>
                <Input
                  id="title"
                  placeholder="Enter song title"
                  value={titleInput}
                  onChange={(e) => setTitleInput(e.target.value)}
                  className="w-full"
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                />
              </div>
            </div>

            <div className="flex flex-col md:flex-row gap-2">
              <div className="flex-1">
                <Label htmlFor="album" className="mb-1 block text-sm">
                  Album (optional)
                </Label>
                <Input
                  id="album"
                  placeholder="Enter album name (optional)"
                  value={albumInput}
                  onChange={(e) => setAlbumInput(e.target.value)}
                  className="w-full"
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                />
              </div>

              <div className="md:self-end">
                <Button
                  onClick={handleSearch}
                  variant="accent"
                  className="w-full md:w-auto"
                  disabled={isSearching}
                >
                  {isSearching ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Searching...
                    </>
                  ) : (
                    <>
                      <Search className="mr-2 h-4 w-4" />
                      Search YouTube
                    </>
                  )}
                </Button>
              </div>
            </div>

            <p className="text-xs text-muted-foreground">
              Enter artist and title to find videos on YouTube. These details
              will also be used for the song's metadata.
            </p>
          </div>

          {/* Results Area */}
          <div className="w-full">
            {searchPerformed && (
              <>
                {results.length === 0 ? (
                  <div className="text-center py-8">
                    <p className="text-muted-foreground">No results found</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Try different search terms or check your spelling
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <h3 className="text-lg font-medium">
                      Results for "{artistInput} {titleInput}"
                    </h3>
                    <div className="grid grid-cols-1 gap-4">
                      {results.map((result) => (
                        <YouTubeSearchResultCard
                          key={result.id}
                          result={result}
                          onDownload={() => handleSelectVideo(result)}
                          isDownloading={downloadingIds.includes(result.id)}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </CardContent>

      {/* Metadata Dialog */}
      {selectedResult && (
        <MetadataDialog
          isOpen={isMetadataDialogOpen}
          onClose={() => {
            setIsMetadataDialogOpen(false);
            // If dialog is closed, cancel download
            if (selectedResult) {
              setDownloadingIds((prev) =>
                prev.filter((id) => id !== selectedResult.id)
              );
              setSelectedResult(null);
            }
          }}
          onSubmit={handleMetadataConfirm}
          initialMetadata={{
            artist: artistInput,
            title: titleInput,
            album: albumInput,
          }}
          videoTitle={selectedResult.title}
          isSubmitting={false}
        />
      )}

      {/* Verification Dialog */}
      <VerificationDialog
        isOpen={isVerificationDialogOpen}
        onClose={() => setIsVerificationDialogOpen(false)}
        onSubmit={handleVerificationSubmit}
        lyricsOptions={lyricsOptions}
        metadataOptions={metadataOptions}
        isSubmitting={saveMetadataMutation.isPending}
        isLoadingLyrics={isLoadingLyrics}
        isLoadingMetadata={isLoadingMetadata}
        songMetadata={confirmedMetadata}
      />
    </Card>
  );
};

interface YouTubeSearchResultCardProps {
  result: YouTubeSearchResult;
  onDownload: () => void;
  isDownloading: boolean;
}

const YouTubeSearchResultCard: React.FC<YouTubeSearchResultCardProps> = ({
  result,
  onDownload,
  isDownloading,
}) => {
  return (
    <div className="flex flex-col md:flex-row gap-4 p-4 border rounded-lg overflow-hidden">
      <div className="md:w-1/3 aspect-video bg-gray-200 rounded overflow-hidden">
        <img
          src={result.thumbnail}
          alt={result.title}
          className="w-full h-full object-cover"
        />
      </div>
      <div className="flex-1 flex flex-col justify-between">
        <div>
          <h3 className="font-medium line-clamp-2 mb-1">{result.title}</h3>
          <p className="text-sm text-muted-foreground">{result.uploader}</p>
          <p className="text-xs text-muted-foreground mt-2">
            {formatDuration(result.duration)}
          </p>
        </div>
        <Button
          onClick={onDownload}
          disabled={isDownloading}
          variant="default"
          className="mt-4 md:self-end"
        >
          {isDownloading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Processing...
            </>
          ) : (
            "Add to Library"
          )}
        </Button>
      </div>
    </div>
  );
};

export default YouTubeSearch;
