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
import { SongAdditionStepper } from "./dialog/SongAdditionStepper";
import {
  useYoutubeDownloadMutation,
  useCreateSongMutation,
  CreateSongResponse,
} from "@/hooks/api/useYoutube";

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

  // Stepper dialog state
  const [isStepperDialogOpen, setIsStepperDialogOpen] = useState(false);
  const [createdSong, setCreatedSong] = useState<CreateSongResponse | null>(
    null
  );

  // --- API Hooks ---
  const createSongMutation = useCreateSongMutation({
    onSuccess: (data) => {
      console.log("Song created in database:", data);
      setCreatedSong(data); // After song creation, start YouTube download with the song ID
      if (selectedResult) {
        youtubeDownloadMutation.mutate({
          video_id: selectedResult.id,
          title: data.title,
          artist: data.artist,
          album: data.album,
          song_id: data.id,
          searchThumbnailUrl: selectedResult.thumbnail, // Pass the original search thumbnail
        });
      }

      // Show stepper dialog
      setIsStepperDialogOpen(true);
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

    // Create a song record in the database and trigger the stepper dialog
    createSongMutation.mutate({
      title: titleInput,
      artist: artistInput,
      album: albumInput,
      source: "youtube",
      sourceUrl: result.url,
      videoId: result.id,
      videoTitle: result.title,
    });
  };

  const handleStepperComplete = () => {
    if (selectedResult) {
      setDownloadingIds((prev) =>
        prev.filter((id) => id !== selectedResult.id)
      );
      setSelectedResult(null);
    }
    setCreatedSong(null);
    setIsStepperDialogOpen(false);
  };

  const handleStepperClose = () => {
    setIsStepperDialogOpen(false);
    if (selectedResult) {
      setDownloadingIds((prev) =>
        prev.filter((id) => id !== selectedResult.id)
      );
      setSelectedResult(null);
    }
    setCreatedSong(null);
  };

  return (
    <Card className="overflow-hidden bg-card/80 pb-0 gap-4">
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
            <div className="flex flex-col gap-2">
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

      {/* Stepper Dialog */}
      {selectedResult && createdSong && (
        <SongAdditionStepper
          isOpen={isStepperDialogOpen}
          onClose={handleStepperClose}
          initialMetadata={{
            artist: artistInput,
            title: titleInput,
            album: albumInput,
          }}
          videoTitle={selectedResult.title}
          videoDuration={selectedResult.duration}
          createdSong={createdSong}
          onComplete={handleStepperComplete}
        />
      )}
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
