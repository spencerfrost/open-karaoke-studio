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
import LyricsCard from "@/components/LyricsCard";

export interface LyricsOption {
  id?: string;
  plainLyrics?: string;
  syncedLyrics?: string;
  isSynced?: boolean;
  duration?: number;
  source?: string;
  quality?: "high" | "medium" | "low";
}

type LyricsResultsProps =
  | ({
      youtubeDurationSeconds: number;
      youtubeMusicDurationSeconds?: never;
      durationMs?: never;
    } & CommonLyricsResultsProps)
  | ({
      youtubeDurationSeconds?: never;
      youtubeMusicDurationSeconds: string;
      durationMs?: never;
    } & CommonLyricsResultsProps)
  | ({
      youtubeDurationSeconds?: never;
      youtubeMusicDurationSeconds?: never;
      durationMs: number;
    } & CommonLyricsResultsProps);

type CommonLyricsResultsProps = {
  options: LyricsOption[];
  selectedOption?: LyricsOption | null;
  onSelectionChange: (option: LyricsOption) => void;
  isLoading?: boolean;
  className?: string;
  maxPreviewLines?: number;
};

export const LyricsResults: React.FC<LyricsResultsProps> = ({
  options,
  selectedOption,
  onSelectionChange,
  isLoading = false,
  className = "",
  maxPreviewLines = 10,
  youtubeDurationSeconds,
  youtubeMusicDurationSeconds,
  durationMs,
}) => {
  // Helper function to format duration
  const formatDuration = (seconds: number) => {
    if (!seconds) return "0:00";
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  // Helper function to parse duration string to seconds
  const parseYoutubeMusicDuration = (duration: string): number => {
    const parts = duration.split(":").map(Number);
    if (parts.length === 3) {
      return parts[0] * 3600 + parts[1] * 60 + parts[2];
    } else if (parts.length === 2) {
      return parts[0] * 60 + parts[1];
    } else if (parts.length === 1) {
      return parts[0];
    }
    return 0;
  };

  function getParsedDuration(
    youtubeDurationSeconds?: number,
    youtubeMusicDurationSeconds?: string,
    durationMs?: number
  ): number {
    if (youtubeDurationSeconds !== undefined) {
      return youtubeDurationSeconds;
    }
    if (youtubeMusicDurationSeconds !== undefined) {
      return parseYoutubeMusicDuration(youtubeMusicDurationSeconds);
    }
    if (durationMs !== undefined) {
      return durationMs / 1000;
    }
    // This should never happen due to prop types, but just in case:
    throw new Error("No valid duration prop provided.");
  }

  const parsedDuration = getParsedDuration(
    youtubeDurationSeconds,
    youtubeMusicDurationSeconds,
    durationMs
  );

  // Helper function to get duration comparison status
  const getDurationComparison = (songDuration: number, lyricsDuration: number) => {

    const diff = Math.abs(songDuration - lyricsDuration);

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


  // Auto-select best option based on duration matching
  React.useEffect(() => {
    if (
      options.length > 0 &&
      !selectedOption &&
      parsedDuration
    ) {
      const bestMatch = options.reduce((best, current) => {
        if (!current.duration) return best;

        const currentDiff = Math.abs(parsedDuration - current.duration);
        const bestDiff = best?.duration
          ? Math.abs(parsedDuration - best.duration)
          : Infinity;

        return currentDiff < bestDiff ? current : best;
      }, options[0]);

      onSelectionChange(bestMatch);
    } else if (options.length > 0 && !selectedOption) {
      // If no video duration, just select first option
      onSelectionChange(options[0]);
    }
  }, [
    options,
    selectedOption,
    parsedDuration,
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
          <p className="text-muted-foreground text-center">
            No lyrics found for this song
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
          const durationComparison = getDurationComparison(parsedDuration, option.duration);
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
                            <span className="text-muted-foreground">
                              vs {formatDuration(parsedDuration)}
                            </span>
                          </div>
                        )}
                      </div>

                      {/* Lyrics preview */}
                      <div className="text-sm prose prose-sm max-w-none">
                        <div className="max-h-32 overflow-hidden">
                          <LyricsCard lyrics={option.syncedLyrics || option.plainLyrics} isSynced={option.isSynced} maxPreviewLines={maxPreviewLines} />
                        </div>
                      </div>

                      {/* Duration comparison message */}
                      {parsedDuration && option.duration && (
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
