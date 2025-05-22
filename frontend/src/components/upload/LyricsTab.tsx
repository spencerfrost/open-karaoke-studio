// frontend/src/components/upload/LyricsTab.tsx
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Loader2 } from "lucide-react";
import { LyricsOption } from "@/hooks/useYoutube";

interface LyricsTabProps {
  isLoading: boolean;
  options: LyricsOption[];
  selectedOption: LyricsOption | null;
  onSelectionChange: (option: LyricsOption) => void;
}

export function LyricsTab({
  isLoading,
  options,
  selectedOption,
  onSelectionChange,
}: LyricsTabProps) {
  const handleValueChange = (value: string) => {
    const index = parseInt(value);
    const selected = options[index];
    if (selected) {
      onSelectionChange(selected);
    }
  };

  // Function to render a preview of lyrics
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
    const lines = cleanedLyrics.split("\n").slice(0, 10);
    return (
      <>
        {lines.map((line, i) => (
          <p key={i} className={line.trim() === "" ? "h-4" : ""}>
            {line}
          </p>
        ))}
        {cleanedLyrics.split("\n").length > 10 && (
          <p className="text-muted-foreground italic mt-2 border-t pt-1">
            {cleanedLyrics.split("\n").length - 10} more lines (not shown)
          </p>
        )}
      </>
    );
  };

  return (
    <ScrollArea className="flex-1 pr-4">
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin mb-4 text-primary" />
          <p className="text-center font-medium">Loading lyrics options...</p>
          <p className="text-center text-sm text-muted-foreground mt-1">
            Searching for lyrics that match your song
          </p>
        </div>
      ) : options.length === 0 ? (
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
      ) : (
        <RadioGroup
          value={String(options.indexOf(selectedOption || options[0]))}
          onValueChange={handleValueChange}
          className="space-y-4"
        >
          {options.map((option, index) => (
            <div key={option.id || index} className="flex items-start space-x-2">
              <RadioGroupItem value={String(index)} id={`lyrics-${index}`} className="mt-1" />
              <div className="flex-1">
                <Label
                  htmlFor={`lyrics-${index}`}
                  className="flex flex-col space-y-1 cursor-pointer"
                >
                  <Card className={`hover:border-primary ${selectedOption === option ? 'border-primary bg-primary/5' : ''}`}>
                    <CardContent className="p-3">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                          <h4 className="font-medium text-sm">
                            {option.trackName || "Lyrics"}
                          </h4>
                          {option.syncedLyrics && (
                            <span className="px-2 py-0.5 text-xs bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded-full">
                              Synchronized
                            </span>
                          )}
                        </div>
                        {option.source && (
                          <span className="text-xs bg-muted px-2 py-1 rounded text-muted-foreground">
                            {option.source}
                          </span>
                        )}
                      </div>
                      
                      <div className="text-sm mt-2 border-t pt-2 text-muted-foreground">
                        {renderLyricsPreview(
                          option.syncedLyrics || option.plainLyrics, 
                          !!option.syncedLyrics
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </Label>
              </div>
            </div>
          ))}
        </RadioGroup>
      )}
    </ScrollArea>
  );
}
