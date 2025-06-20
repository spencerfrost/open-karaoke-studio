import React, { useState, useEffect } from "react";
import { Song } from "@/types/Song";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Search,
  Loader2,
  Music,
  AlertTriangle,
  RefreshCw,
  FileText,
} from "lucide-react";
import { useMutation } from "@tanstack/react-query";

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
  /** Optional song to pre-fill form fields */
  song?: Song | null;
  /** Callback when lyrics are successfully fetched */
  onLyricsFetched?: (lyrics: LyricsResult[]) => void;
  /** Callback when a specific lyrics result is selected */
  onLyricsSelected?: (lyrics: LyricsResult) => void;
}

export const LyricsFetchDialog: React.FC<LyricsFetchDialogProps> = ({
  isOpen,
  onClose,
  song,
  onLyricsFetched,
  onLyricsSelected,
}) => {
  // Form state
  const [artistName, setArtistName] = useState("");
  const [trackName, setTrackName] = useState("");
  const [albumName, setAlbumName] = useState("");

  // Results state
  const [lyricsResults, setLyricsResults] = useState<LyricsResult[]>([]);
  const [selectedResult, setSelectedResult] = useState<LyricsResult | null>(
    null
  );
  const [hasSearched, setHasSearched] = useState(false);

  // Pre-fill form when song changes
  useEffect(() => {
    if (song) {
      setArtistName(song.artist || "");
      setTrackName(song.title || "");
      setAlbumName(song.album || "");
    } else {
      setArtistName("");
      setTrackName("");
      setAlbumName("");
    }
    // Reset results when song changes
    setLyricsResults([]);
    setSelectedResult(null);
    setHasSearched(false);
  }, [song]);

  // Reset state when dialog closes
  useEffect(() => {
    if (!isOpen) {
      setLyricsResults([]);
      setSelectedResult(null);
      setHasSearched(false);
    }
  }, [isOpen]);

  const searchLyricsMutation = useMutation({
    mutationFn: async (params: {
      artist_name: string;
      track_name: string;
      album_name?: string;
    }) => {
      const searchParams = new URLSearchParams({
        artist_name: params.artist_name,
        track_name: params.track_name,
      });

      if (params.album_name?.trim()) {
        searchParams.append("album_name", params.album_name);
      }

      const response = await fetch(`/api/lyrics/search?${searchParams}`);

      if (!response.ok) {
        const error = await response
          .json()
          .catch(() => ({ error: "Network error" }));
        throw new Error(error.error || `HTTP ${response.status}`);
      }

      return response.json();
    },
    onSuccess: (results) => {
      setLyricsResults(results || []);
      setHasSearched(true);
      onLyricsFetched?.(results || []);
    },
    onError: (error) => {
      console.error("Lyrics search failed:", error);
      setLyricsResults([]);
      setHasSearched(true);
    },
  });

  const handleSearch = () => {
    if (!artistName.trim() || !trackName.trim()) {
      return;
    }

    searchLyricsMutation.mutate({
      artist_name: artistName.trim(),
      track_name: trackName.trim(),
      album_name: albumName.trim() || undefined,
    });
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !searchLyricsMutation.isPending) {
      handleSearch();
    }
  };

  const handleSelectResult = (result: LyricsResult) => {
    setSelectedResult(result);
    onLyricsSelected?.(result);
  };

  const handleReset = () => {
    setLyricsResults([]);
    setSelectedResult(null);
    setHasSearched(false);
  };

  const canSearch = artistName.trim() && trackName.trim();

  const renderLyricsPreview = (lyrics?: string, isSynced = false) => {
    if (!lyrics) {
      return (
        <span className="text-muted-foreground italic">
          No lyrics available
        </span>
      );
    }

    // Clean synced lyrics by removing timestamps for preview
    const cleanedLyrics = isSynced
      ? lyrics
          .split("\n")
          .map((line) => line.replace(/^\[\d+:\d+\.\d+\]/g, "").trim())
          .filter((line) => line.length > 0)
          .join("\n")
      : lyrics;

    // Show first few lines for preview
    const lines = cleanedLyrics.split("\n").slice(0, 4);
    return (
      <div className="text-sm">
        {lines.map((line, i) => (
          <p key={i} className={line.trim() === "" ? "h-4" : ""}>
            {line}
          </p>
        ))}
        {cleanedLyrics.split("\n").length > 4 && (
          <p className="text-muted-foreground italic mt-1">
            ... and {cleanedLyrics.split("\n").length - 4} more lines
          </p>
        )}
      </div>
    );
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Fetch Lyrics
          </DialogTitle>
          <DialogDescription>
            Search for lyrics using song metadata.
            {song
              ? ` Pre-filled with "${song.title}" by ${song.artist}.`
              : " Enter song details to search."}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4 flex-1 overflow-hidden">
          {/* Search Form */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Search Parameters</CardTitle>
              <CardDescription>
                Enter or modify the song details to search for lyrics
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="artist-name">Artist *</Label>
                  <Input
                    id="artist-name"
                    value={artistName}
                    onChange={(e) => setArtistName(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Enter artist name"
                    disabled={searchLyricsMutation.isPending}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="track-name">Title *</Label>
                  <Input
                    id="track-name"
                    value={trackName}
                    onChange={(e) => setTrackName(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Enter song title"
                    disabled={searchLyricsMutation.isPending}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="album-name">Album (Optional)</Label>
                  <Input
                    id="album-name"
                    value={albumName}
                    onChange={(e) => setAlbumName(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Enter album name"
                    disabled={searchLyricsMutation.isPending}
                  />
                </div>
              </div>

              <div className="flex justify-between items-center">
                <p className="text-xs text-muted-foreground">
                  * Required fields. Album name can help improve search
                  accuracy.
                </p>
                <div className="flex gap-2">
                  {hasSearched && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleReset}
                      disabled={searchLyricsMutation.isPending}
                    >
                      <RefreshCw className="h-4 w-4 mr-1" />
                      Reset
                    </Button>
                  )}
                  <Button
                    onClick={handleSearch}
                    disabled={!canSearch || searchLyricsMutation.isPending}
                  >
                    {searchLyricsMutation.isPending ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Searching...
                      </>
                    ) : (
                      <>
                        <Search className="h-4 w-4 mr-2" />
                        Search Lyrics
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Results */}
          {hasSearched && (
            <Card className="flex-1 flex flex-col overflow-hidden">
              <CardHeader className="flex-shrink-0">
                <CardTitle className="text-lg">
                  Search Results ({lyricsResults.length})
                </CardTitle>
                <CardDescription>
                  {lyricsResults.length > 0
                    ? "Select a result to use these lyrics"
                    : "No lyrics found. Try adjusting your search terms."}
                </CardDescription>
              </CardHeader>
              <CardContent className="flex-1 overflow-hidden p-0">
                <ScrollArea className="h-full p-6">
                  {searchLyricsMutation.isPending ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="h-8 w-8 animate-spin mr-2" />
                      <span>Searching for lyrics...</span>
                    </div>
                  ) : lyricsResults.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-8 text-center">
                      <AlertTriangle className="h-12 w-12 text-muted-foreground mb-4" />
                      <h3 className="text-lg font-medium mb-2">
                        No lyrics found
                      </h3>
                      <p className="text-muted-foreground text-sm mb-4">
                        Try different search terms or check the spelling
                      </p>
                      <Button variant="outline" onClick={handleReset}>
                        Try again
                      </Button>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {lyricsResults.map((result, index) => (
                        <Card
                          key={result.id || index}
                          className={`cursor-pointer transition-all hover:shadow-md ${
                            selectedResult === result
                              ? "ring-2 ring-primary"
                              : ""
                          }`}
                          onClick={() => handleSelectResult(result)}
                        >
                          <CardHeader className="pb-3">
                            <div className="flex items-start justify-between">
                              <div>
                                <CardTitle className="text-base">
                                  {result.trackName || "Unknown Title"}
                                </CardTitle>
                                <CardDescription>
                                  by {result.artistName || "Unknown Artist"}
                                  {result.albumName && ` • ${result.albumName}`}
                                </CardDescription>
                              </div>
                              <div className="flex gap-1">
                                {result.syncedLyrics && (
                                  <Badge
                                    variant="secondary"
                                    className="bg-green-100 text-green-800"
                                  >
                                    <Music className="h-3 w-3 mr-1" />
                                    Synced
                                  </Badge>
                                )}
                                {result.duration && (
                                  <Badge variant="outline" className="text-xs">
                                    {Math.floor(result.duration / 60)}:
                                    {String(result.duration % 60).padStart(
                                      2,
                                      "0"
                                    )}
                                  </Badge>
                                )}
                              </div>
                            </div>
                          </CardHeader>
                          <CardContent className="pt-0">
                            <div className="border-t pt-3">
                              <h4 className="text-sm font-medium mb-2">
                                Lyrics Preview:
                              </h4>
                              {renderLyricsPreview(result.plainLyrics)}
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  )}
                </ScrollArea>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-between items-center pt-4 border-t">
          <div className="text-sm text-muted-foreground">
            {selectedResult && (
              <span className="flex items-center gap-1">
                <Music className="h-4 w-4" />
                Selected: {selectedResult.trackName} by{" "}
                {selectedResult.artistName}
              </span>
            )}
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            {selectedResult && (
              <Button onClick={() => onClose()}>Use Selected Lyrics</Button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default LyricsFetchDialog;
