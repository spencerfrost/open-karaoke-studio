// frontend/src/components/upload/steps/LyricsSelectionStep.tsx
import { useState } from "react";
import {
  Search,
  CheckCircle,
  AlertTriangle,
  XCircle,
  ThumbsUp,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Skeleton } from "@/components/ui/skeleton";
import { LyricsOption } from "@/hooks/useYoutube";
import { ScrollArea } from "@radix-ui/react-scroll-area";

interface LyricsSelectionStepProps {
  lyricsOptions: LyricsOption[];
  selectedLyrics: LyricsOption | null;
  videoDuration: number;
  isSearching: boolean;
  initialMetadata: {
    artist: string;
    title: string;
    album: string;
  };
  onLyricsSelect: (lyrics: LyricsOption) => void;
  onConfirm: () => void;
  onSkip: () => void;
  onResearch: (query: { artist: string; title: string; album: string }) => void;
}

// Helper function to format duration
const formatDuration = (seconds: number) => {
  if (!seconds) return "0:00";
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
};

// Helper function to get duration comparison status
const getDurationComparison = (
  videoDuration: number,
  lyricsDuration?: number
) => {
  if (!lyricsDuration) {
    return {
      status: "unknown",
      message: "Duration unknown",
      icon: null,
      className: "text-muted-foreground",
    };
  }

  const diff = Math.abs(videoDuration - lyricsDuration);

  if (diff <= 0.5) {
    return {
      status: "perfect",
      message: "Perfect match",
      icon: CheckCircle,
      className: "text-green-700",
    };
  } else if (diff <= 2) {
    return {
      status: "good",
      message: "Good match",
      icon: ThumbsUp,
      className: "text-green-700",
    };
  } else if (diff <= 4) {
    return {
      status: "okay",
      message: "Okay match",
      icon: AlertTriangle,
      className: "text-orange-500",
    };
  } else {
    return {
      status: "poor",
      message: "Duration mismatch",
      icon: XCircle,
      className: "text-red-600",
    };
  }
};

const renderLyricsPreview = (lyrics?: string, isSynced = false) => {
  if (!lyrics)
    return (
      <span className="text-muted-foreground italic">No lyrics available</span>
    );

  // Clean synced lyrics by removing timestamps
  const cleanedLyrics = isSynced
    ? lyrics
        .split("\n")
        .map((line) => line.replace(/^\[\d+:\d+\.\d+\]/g, "").trim())
        .join("\n")
    : lyrics;

  const lines = cleanedLyrics.split("\n").slice(0, 20);
  return (
    <>
      {lines.map((line, i) => (
        <p key={i} className={line.trim() === "" ? "h-4" : ""}>
          {line}
        </p>
      ))}
      {cleanedLyrics.split("\n").length > 20 && (
        <p className="text-muted-foreground italic mt-2 border-t pt-2">
          {cleanedLyrics.split("\n").length - 20} more lines (not shown)
        </p>
      )}
    </>
  );
};

export function LyricsSelectionStep({
  lyricsOptions,
  selectedLyrics,
  videoDuration,
  isSearching,
  initialMetadata,
  onLyricsSelect,
  onConfirm,
  onSkip,
  onResearch,
}: LyricsSelectionStepProps) {
  const [showResearch, setShowResearch] = useState(false);
  const [researchArtist, setResearchArtist] = useState("");
  const [researchTitle, setResearchTitle] = useState("");
  const [researchAlbum, setResearchAlbum] = useState("");

  const handleResearch = () => {
    onResearch({
      artist: researchArtist.trim(),
      title: researchTitle.trim(),
      album: researchAlbum.trim(),
    });
    setShowResearch(false);
  };

  const handleNoneOfThese = () => {
    setShowResearch(true);
    setResearchArtist(initialMetadata.artist);
    setResearchTitle(initialMetadata.title);
    setResearchAlbum(initialMetadata.album);
  };

  if (showResearch) {
    return (
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>Search for Different Lyrics</CardTitle>
            <CardDescription>
              Try different search terms to find the right lyrics
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-6 space-y-3">
            <div>
              <Label htmlFor="research-artist">Artist</Label>
              <Input
                id="research-artist"
                value={researchArtist}
                onChange={(e) => setResearchArtist(e.target.value)}
                placeholder="Artist name"
              />
            </div>

            <div>
              <Label htmlFor="research-title">Title</Label>
              <Input
                id="research-title"
                value={researchTitle}
                onChange={(e) => setResearchTitle(e.target.value)}
                placeholder="Song title"
              />
            </div>

            <div>
              <Label htmlFor="research-album">Album</Label>
              <Input
                id="research-album"
                value={researchAlbum}
                onChange={(e) => setResearchAlbum(e.target.value)}
                placeholder="Album name (optional)"
              />
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-between">
          <Button variant="outline" onClick={() => setShowResearch(false)}>
            Back
          </Button>
          <Button
            onClick={handleResearch}
            disabled={
              !researchArtist.trim() || !researchTitle.trim() || isSearching
            }
          >
            {isSearching ? (
              <>
                <Search className="h-4 w-4 mr-2 animate-spin" />
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
    );
  }

  return (
    <div className="space-y-4 max-h-[65vh] flex flex-col">
      <Card className="flex flex-col overflow-hidden">
        <CardHeader className="flex-shrink-0">
          <CardTitle>Lyrics Options</CardTitle>
          <CardDescription>
            Compare durations first, then review lyrics content to find the best
            match.
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-6 overflow-hidden">
          <div className="max-h-[70vh] overflow-y-auto">
            <div className="space-y-4 pr-4">
              {isSearching && lyricsOptions.length === 0 ? (
                // Loading state
                <div className="space-y-4">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground mb-4">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Searching for lyrics...</span>
                  </div>
                  {[1, 2, 3].map((index) => (
                    <Card key={index} className="p-4">
                      <div className="space-y-3">
                        <div className="flex justify-between items-start">
                          <Skeleton className="h-4 w-32" />
                          <Skeleton className="h-6 w-16" />
                        </div>
                        <div className="p-2 bg-muted/30 rounded-md">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4">
                              <Skeleton className="h-3 w-20" />
                              <Skeleton className="h-3 w-24" />
                            </div>
                            <Skeleton className="h-3 w-16" />
                          </div>
                        </div>
                        <div className="space-y-2 pt-3 border-t">
                          {[1, 2, 3, 4, 5].map((line) => (
                            <Skeleton key={line} className="h-3 w-full" />
                          ))}
                          <Skeleton className="h-3 w-3/4" />
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              ) : lyricsOptions.length > 0 ? (
                <RadioGroup
                  value={selectedLyrics?.id || ""}
                  onValueChange={(value) => {
                    const lyrics = lyricsOptions.find((l) => l.id === value);
                    if (lyrics) onLyricsSelect(lyrics);
                  }}
                  className="space-y-4"
                >
                  {lyricsOptions.map((lyrics, index) => (
                    <div
                      key={lyrics.id || index}
                      className="flex items-center space-x-3"
                    >
                      <RadioGroupItem
                        value={lyrics.id}
                        id={`lyrics-${index}`}
                        className="mt-4"
                      />
                      <Label
                        htmlFor={`lyrics-${index}`}
                        className="flex-1 flex flex-col space-y-1 cursor-pointer"
                      >
                        <Card
                          className={`
                          hover:border-primary py-0 w-full 
                          ${selectedLyrics === lyrics ? "border-primary bg-primary/5" : ""}
                        `}
                        >
                          <CardContent className="p-4">
                            <div className="flex justify-between items-start mb-3">
                              <div className="flex items-center gap-2">
                                <h4 className="font-medium text-sm">
                                  {lyrics.trackName || lyrics.name || "Lyrics"}
                                </h4>
                                {lyrics.syncedLyrics && (
                                  <span className="px-2 py-0.5 text-xs bg-green-100 text-green-800 rounded-full">
                                    Synchronized
                                  </span>
                                )}
                              </div>
                              {lyrics.source && (
                                <span className="text-xs bg-muted px-2 py-1 rounded text-muted-foreground">
                                  {lyrics.source}
                                </span>
                              )}
                            </div>

                            <div className="mb-3 p-2 bg-muted/30 rounded-md">
                              <div className="flex items-center justify-between text-xs">
                                <div className="flex items-center gap-4">
                                  <span className="text-muted-foreground">
                                    Video: {formatDuration(videoDuration)}
                                  </span>
                                  <span className="text-muted-foreground">
                                    Lyrics:{" "}
                                    {lyrics.duration
                                      ? formatDuration(lyrics.duration)
                                      : "Unknown"}
                                  </span>
                                </div>
                                {(() => {
                                  const comparison = getDurationComparison(
                                    videoDuration,
                                    lyrics.duration
                                  );
                                  const Icon = comparison.icon;
                                  return (
                                    <div
                                      className={`flex items-center gap-1 ${comparison.className}`}
                                    >
                                      {Icon && <Icon className="h-3 w-3" />}
                                      <span className="font-medium text-xs">
                                        {comparison.message}
                                      </span>
                                    </div>
                                  );
                                })()}
                              </div>
                            </div>

                            <div className="text-sm mt-3 border-t pt-3 text-muted-foreground">
                              <div className="max-h-48 overflow-y-auto">
                                <ScrollArea className="h-full">
                                  <div className="pr-2">
                                    {renderLyricsPreview(
                                      lyrics.syncedLyrics || lyrics.plainLyrics,
                                      !!lyrics.syncedLyrics
                                    )}
                                  </div>
                                </ScrollArea>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      </Label>
                    </div>
                  ))}
                </RadioGroup>
              ) : (
                <Card>
                  <CardContent className="py-4">
                    <p className="text-muted-foreground text-center">
                      No lyrics found
                    </p>
                    <p className="text-xs text-muted-foreground text-center mt-2">
                      You can add lyrics manually later
                    </p>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-between">
        <div className="space-x-2">
          <Button
            variant="outline"
            onClick={handleNoneOfThese}
            disabled={isSearching}
          >
            None of these
          </Button>
          <Button variant="outline" onClick={onSkip} disabled={isSearching}>
            Skip lyrics
          </Button>
        </div>
        <Button onClick={onConfirm} disabled={!selectedLyrics || isSearching}>
          {isSearching ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Searching...
            </>
          ) : (
            "Confirm & Save Lyrics"
          )}
        </Button>
      </div>
    </div>
  );
}
