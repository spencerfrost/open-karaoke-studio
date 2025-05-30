import React, { useState } from "react";
import { Search, Download, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import {
  searchYouTube,
  downloadYouTubeVideo,
  fetchEnhancedMetadata,
  fetchLyrics,
  YouTubeSearchResult,
} from "@/services/youtubeService";
import { parseYouTubeTitle } from "@/utils/formatters";
import { MetadataDialog } from "./MetadataDialog";

// Helper functions
const formatDuration = (seconds: number) => {
  if (!seconds) return "0:00";
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
};

const YouTubeSearch: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState("");
  const [results, setResults] = useState<YouTubeSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchPerformed, setSearchPerformed] = useState(false);
  const [downloadingIds, setDownloadingIds] = useState<string[]>([]);

  const [isMetadataDialogOpen, setIsMetadataDialogOpen] = useState(false);
  const [selectedResult, setSelectedResult] =
    useState<YouTubeSearchResult | null>(null);
  const [isSubmittingMetadata, setIsSubmittingMetadata] = useState(false);

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      toast.error("Please enter a search query");
      return;
    }

    setIsSearching(true);
    try {
      const response = await searchYouTube(searchQuery);
      if (response.error) {
        throw new Error(response.error);
      }

      setResults(Array.isArray(response.data) ? response.data : []);
      setSearchPerformed(true);
    } catch (error) {
      console.error("Search error:", error);
      toast.error(
        `Failed to search: ${
          error instanceof Error ? error.message : "Unknown error"
        }`
      );
    } finally {
      setIsSearching(false);
    }
  };

  const handleSelectForDownload = (result: YouTubeSearchResult) => {
    setSelectedResult(result);
    setIsMetadataDialogOpen(true);
  };

  const handleMetadataSubmit = async (metadata: {
    artist: string;
    title: string;
  }) => {
    if (!selectedResult) return;

    try {
      setIsSubmittingMetadata(true);
      setDownloadingIds((prev) => [...prev, selectedResult.id]);

      await downloadYouTubeVideo(selectedResult.id, {
        title: metadata.title,
        artist: metadata.artist,
      });

      toast.success(
        `Added "${metadata.title}" by ${metadata.artist} to processing queue`
      );

      setIsMetadataDialogOpen(false);
      setSelectedResult(null);
    } catch (error) {
      console.error("Download error:", error);
      toast.error(
        `Failed to download: ${
          error instanceof Error ? error.message : "Unknown error"
        }`
      );
    } finally {
      setIsSubmittingMetadata(false);
      setDownloadingIds((prev) =>
        prev.filter((id) => selectedResult.id !== id)
      );
    }
  };

  return (
    <Card className="bg-card/80">
      <CardHeader>
        <CardTitle>Search YouTube</CardTitle>
        <CardDescription>
          Find songs on YouTube to add to your karaoke library
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="w-full">
          {/* Search Input */}
          <div className="flex flex-col md:flex-row gap-2 mb-6">
            <Input
              placeholder="Search for songs on YouTube..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="flex-1"
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            />

            <Button
              onClick={handleSearch}
              className="bg-accent text-primary-foreground hover:bg-accent/90"
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
                  Search
                </>
              )}
            </Button>
          </div>

          {/* Results Area */}
          {isSearching ? (
            <div className="flex justify-center py-12">
              <div className="relative h-12 w-12">
                <div className="absolute animate-spin rounded-full h-full w-full border-4 border-t-primary border-r-transparent border-b-transparent border-l-transparent"></div>
              </div>
            </div>
          ) : (
            <>
              {results.length === 0 && searchPerformed ? (
                <div className="p-4 bg-muted rounded-md text-center">
                  <p className="text-card-foreground/80 mb-2">
                    No results found
                  </p>
                  <p className="text-sm text-card-foreground/60">
                    Try a different search term
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 fade-in">
                  {results.map((result) => (
                    <YouTubeSearchResultCard
                      key={result.id}
                      result={result}
                      onDownload={() => handleSelectForDownload(result)}
                      isDownloading={downloadingIds.includes(result.id)}
                    />
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </CardContent>

      {/* Metadata Dialog */}
      {selectedResult && (
        <MetadataDialog
          isOpen={isMetadataDialogOpen}
          onClose={() => setIsMetadataDialogOpen(false)}
          onSubmit={handleMetadataSubmit}
          initialMetadata={parseYouTubeTitle(selectedResult.title)}
          videoTitle={selectedResult.title}
          isSubmitting={isSubmittingMetadata}
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
    <Card className="overflow-hidden h-full flex flex-col border border-border/50 hover:border-border transition-colors">
      <div className="relative">
        <div className="aspect-video">
          <img
            src={result.thumbnail}
            alt={result.title}
            className="object-cover w-full h-full"
          />
        </div>
        <div className="absolute bottom-2 right-2 bg-russet/80 text-lemon-chiffon px-2 py-1 rounded-sm text-xs">
          {formatDuration(result.duration)}
        </div>
      </div>

      <CardContent className="flex-1 flex flex-col pt-4">
        <h3 className="font-medium truncate mb-1" title={result.title}>
          {result.title}
        </h3>
        <p className="text-card-foreground/70 text-sm mb-auto">
          {result.uploader}
        </p>

        <div className="mt-4">
          <Button
            onClick={onDownload}
            className="w-full bg-accent text-primary-foreground hover:bg-accent/90"
            disabled={isDownloading}
          >
            {isDownloading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Processing
              </>
            ) : (
              <>
                <Download className="mr-2 h-4 w-4" />
                Add to Library
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

export default YouTubeSearch;
