import React from "react";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import {
  Loader2,
  CheckCircle,
  AlertTriangle,
  XCircle,
  ThumbsUp,
} from "lucide-react";

export interface LyricsOption {
  id?: string;
  lyrics?: string;
  syncedLyrics?: string;
  isSynced?: boolean;
  duration?: number;
  source?: string;
  quality?: "high" | "medium" | "low";
}

interface LyricsResultsProps {
  options: LyricsOption[];
  selectedOption?: LyricsOption | null;
  onSelectionChange: (option: LyricsOption) => void;
  isLoading?: boolean;
  videoDuration?: number;
  autoSelectBest?: boolean;
  emptyMessage?: string;
  className?: string;
  maxPreviewLines?: number;
}

export const LyricsResults: React.FC<LyricsResultsProps> = ({
  options,
  selectedOption,
  onSelectionChange,
  isLoading = false,
  videoDuration,
  autoSelectBest = true,
  emptyMessage = "No lyrics found",
  className = "",
  maxPreviewLines = 10,
}) => {
  // Helper function to format duration
  const formatDuration = (seconds: number) => {
    if (!seconds) return "0:00";
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  // Helper function to get duration comparison status
  const getDurationComparison = (lyricsDuration?: number) => {
    if (!videoDuration || !lyricsDuration) {
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

  // Function to render lyrics preview
  const renderLyricsPreview = (lyrics?: string, isSynced = false) => {
    if (!lyrics)
      return (
        <span className="text-muted-foreground italic">
          No lyrics available
        </span>
      );

    // Remove timestamps for synced lyrics preview
    const cleanedLyrics = isSynced
      ? lyrics
          .split("\n")
          .map((line) => line.replace(/^\[\d+:\d+\.\d+\]/g, "").trim())
          .join("\n")
      : lyrics;

    // Only show first few lines
    const lines = cleanedLyrics.split("\n").slice(0, maxPreviewLines);
    return (
      <>
        {lines.map((line, i) => (
          <p key={i} className={line.trim() === "" ? "h-4" : ""}>
            {line}
          </p>
        ))}
        {cleanedLyrics.split("\n").length > maxPreviewLines && (
          <p className="text-muted-foreground italic mt-2 border-t pt-1">
            {cleanedLyrics.split("\n").length - maxPreviewLines} more lines (not
            shown)
          </p>
        )}
      </>
    );
  };

  // Auto-select best option based on duration matching
  React.useEffect(() => {
    if (
      autoSelectBest &&
      options.length > 0 &&
      !selectedOption &&
      videoDuration
    ) {
      const bestMatch = options.reduce((best, current) => {
        if (!current.duration) return best;

        const currentDiff = Math.abs(videoDuration - current.duration);
        const bestDiff = best?.duration
          ? Math.abs(videoDuration - best.duration)
          : Infinity;

        return currentDiff < bestDiff ? current : best;
      }, options[0]);

      onSelectionChange(bestMatch);
    } else if (autoSelectBest && options.length > 0 && !selectedOption) {
      // If no video duration, just select first option
      onSelectionChange(options[0]);
    }
  }, [
    options,
    selectedOption,
    autoSelectBest,
    videoDuration,
    onSelectionChange,
  ]);

  const handleValueChange = (value: string) => {
    const index = parseInt(value);
    const selected = options[index];
    if (selected) {
      onSelectionChange(selected);
    }
  };

  const getSelectedIndex = () => {
    if (!selectedOption) return "0";
    const index = options.findIndex((option) =>
      option.id ? option.id === selectedOption.id : option === selectedOption
    );
    return index >= 0 ? String(index) : "0";
  };

  if (isLoading) {
    return (
      <div
        className={`flex flex-col items-center justify-center py-8 ${className}`}
      >
        <Loader2 className="h-8 w-8 animate-spin mb-4 text-primary" />
        <p className="text-center font-medium">Loading lyrics options...</p>
        <p className="text-center text-sm text-muted-foreground mt-1">
          Searching for lyrics that match your song
        </p>
      </div>
    );
  }

  if (options.length === 0) {
    return (
      <Card className={className}>
        <CardContent className="py-4">
          <p className="text-muted-foreground text-center">{emptyMessage}</p>
          <p className="text-xs text-muted-foreground text-center mt-2">
            You can add lyrics manually later
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <ScrollArea className={`flex-1 pr-4 ${className}`}>
      <RadioGroup
        value={getSelectedIndex()}
        onValueChange={handleValueChange}
        className="space-y-4"
      >
        {options.map((option, index) => {
          const durationComparison = getDurationComparison(option.duration);
          const DurationIcon = durationComparison.icon;

          return (
            <div
              key={option.id || index}
              className="flex items-center space-x-2"
            >
              <RadioGroupItem value={String(index)} id={`lyrics-${index}`} />
              <div className="flex-1">
                <Label
                  htmlFor={`lyrics-${index}`}
                  className="flex flex-col space-y-1 cursor-pointer"
                >
                  <Card
                    className={`hover:border-primary w-full ${
                      selectedOption === option
                        ? "border-primary bg-primary/5"
                        : ""
                    }`}
                  >
                    <CardContent className="p-3">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                          <div className="flex gap-1">
                            {option.isSynced && (
                              <Badge
                                variant="secondary"
                                className="bg-green-100 text-green-800 text-xs"
                              >
                                Synced
                              </Badge>
                            )}
                            {option.source && (
                              <Badge variant="outline" className="text-xs">
                                {option.source}
                              </Badge>
                            )}
                            {option.quality && (
                              <Badge
                                variant={
                                  option.quality === "high"
                                    ? "default"
                                    : "secondary"
                                }
                                className="text-xs"
                              >
                                {option.quality}
                              </Badge>
                            )}
                          </div>
                        </div>

                        {/* Duration comparison */}
                        {option.duration && (
                          <div
                            className={`flex items-center gap-1 text-xs ${durationComparison.className}`}
                          >
                            {DurationIcon && <DurationIcon size={12} />}
                            <span>{formatDuration(option.duration)}</span>
                            {videoDuration && (
                              <span className="text-muted-foreground">
                                vs {formatDuration(videoDuration)}
                              </span>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Lyrics preview */}
                      <div className="text-sm prose prose-sm max-w-none">
                        <div className="max-h-32 overflow-hidden">
                          {renderLyricsPreview(
                            option.syncedLyrics || option.lyrics,
                            option.isSynced
                          )}
                        </div>
                      </div>

                      {/* Duration comparison message */}
                      {videoDuration && option.duration && (
                        <div
                          className={`mt-2 text-xs ${durationComparison.className}`}
                        >
                          {durationComparison.message}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </Label>
              </div>
            </div>
          );
        })}
      </RadioGroup>
    </ScrollArea>
  );
};
