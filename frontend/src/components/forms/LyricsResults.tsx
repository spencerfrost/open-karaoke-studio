import React from "react";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Loader2 } from "lucide-react";
import LyricsCard from "@/components/LyricsCard";
import type { LyricsOption } from "@/hooks/api/useLyrics";

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

  // Sort options by how close their duration is to the song's duration
  const sortedOptions = React.useMemo(() => {
    if (!parsedDuration) return options;
    return [...options].sort((a, b) => {
      if (a.duration == null && b.duration == null) return 0;
      if (a.duration == null) return 1;
      if (b.duration == null) return -1;
      return (
        Math.abs(parsedDuration - a.duration) -
        Math.abs(parsedDuration - b.duration)
      );
    });
  }, [options, parsedDuration]);

  // Find the best match (closest duration) option
  const bestMatchOption = React.useMemo(() => {
    if (!parsedDuration) return undefined;
    return sortedOptions.find(
      (option) =>
        option.duration != null &&
        Math.abs(parsedDuration - option.duration) ===
          Math.min(
            ...sortedOptions
              .filter((o) => o.duration != null)
              .map((o) => Math.abs(parsedDuration - (o.duration ?? 0)))
          )
    );
  }, [sortedOptions, parsedDuration]);

  // Auto-select best option based on duration matching
  React.useEffect(() => {
    if (options.length > 0 && !selectedOption && parsedDuration) {
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
  }, [options, selectedOption, parsedDuration, onSelectionChange]);

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
      <div className={className}>
        <div className="py-4">
          <p className="text-muted-foreground text-center">
            No lyrics found for this song
          </p>
        </div>
      </div>
    );
  }

  return (
    <ScrollArea className={`flex-1 pr-4 ${className}`}>
      <RadioGroup
        value={getSelectedIndex()}
        onValueChange={handleValueChange}
        className="space-y-4"
      >
        {sortedOptions.map((option, index) => {
          const isBestMatch = option === bestMatchOption;

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
                  <LyricsCard
                    option={option}
                    selectedOption={selectedOption ?? null}
                    isBestMatch={isBestMatch}
                    parsedDuration={parsedDuration}
                    maxPreviewLines={maxPreviewLines}
                  />
                </Label>
              </div>
            </div>
          );
        })}
      </RadioGroup>
    </ScrollArea>
  );
};
