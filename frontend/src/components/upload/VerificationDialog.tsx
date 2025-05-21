// frontend/src/components/upload/VerificationDialog.tsx
import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Loader2, CheckCircle2 } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  LyricsOption,
  MetadataOption,
} from "@/hooks/useYoutube";

interface VerificationDialogProps {
  readonly isOpen: boolean;
  readonly onClose: () => void;
  readonly onSubmit: (selections: {
    selectedLyrics: LyricsOption | null;
    selectedMetadata: MetadataOption | null;
  }) => void;
  readonly lyricsOptions: LyricsOption[];
  readonly metadataOptions: MetadataOption[];
  readonly isSubmitting?: boolean;
  readonly isLoadingLyrics?: boolean;
  readonly isLoadingMetadata?: boolean;
  readonly songMetadata: {
    title: string;
    artist: string;
    album?: string;
  };
}

export function VerificationDialog({
  isOpen,
  onClose,
  onSubmit,
  lyricsOptions,
  metadataOptions,
  isSubmitting = false,
  isLoadingLyrics = false,
  isLoadingMetadata = false,
  songMetadata,
}: VerificationDialogProps) {
  const [activeTab, setActiveTab] = useState("metadata");
  const [selectedLyrics, setSelectedLyrics] = useState<LyricsOption | null>(null);
  const [selectedMetadata, setSelectedMetadata] = useState<MetadataOption | null>(null);

  // Reset selections when dialog opens or options change
  useEffect(() => {
    if (isOpen) {
      setSelectedLyrics(lyricsOptions.length > 0 ? lyricsOptions[0] : null);
      setSelectedMetadata(
        metadataOptions.length > 0 ? metadataOptions[0] : null
      );
    }
  }, [isOpen, lyricsOptions, metadataOptions]);

  const handleSubmit = () => {
    onSubmit({
      selectedLyrics,
      selectedMetadata,
    });
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
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[600px] max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Verify Song Information</DialogTitle>
          <DialogDescription>
            <p className="mb-1">
              Please select the correct metadata and lyrics for:{" "}
              <strong>
                {songMetadata.title} by {songMetadata.artist}
              </strong>
            </p>
            <p className="text-xs text-muted-foreground italic mb-1">
              We've found multiple options for your song's metadata and lyrics. 
              Review and select the most accurate information for both tabs before confirming.
            </p>
            <p className="text-xs text-muted-foreground">
              <span className="text-green-500 font-medium">Tip:</span> Look for synchronized lyrics 
              with the <span className="px-1 py-0.5 text-xs bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded-full">
                Synchronized
              </span> badge for the best karaoke experience.
            </p>
          </DialogDescription>
        </DialogHeader>
        
        {isSubmitting ? (
          <div className="flex flex-col items-center justify-center py-8">
            <Loader2 className="h-10 w-10 animate-spin mb-4 text-primary" />
            <p className="text-center font-medium">Finalizing your song...</p>
            <p className="text-center text-sm text-muted-foreground mt-1">
              This may take a moment while we process your selections
            </p>
          </div>
        ) : (
          <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 overflow-hidden flex flex-col">
            <TabsList className="grid grid-cols-2">
              <TabsTrigger value="metadata" className="flex items-center gap-1">
                Metadata 
                {isLoadingMetadata ? (
                  <Loader2 className="ml-1 h-3 w-3 animate-spin" />
                ) : selectedMetadata !== null && (
                  <CheckCircle2 className="ml-1 h-3 w-3 text-green-500" />
                )}
              </TabsTrigger>
              <TabsTrigger value="lyrics" className="flex items-center gap-1">
                Lyrics 
                {isLoadingLyrics ? (
                  <Loader2 className="ml-1 h-3 w-3 animate-spin" />
                ) : selectedLyrics !== null && (
                  <CheckCircle2 className="ml-1 h-3 w-3 text-green-500" />
                )}
              </TabsTrigger>
            </TabsList>
            
            <TabsContent value="metadata" className="flex-1 overflow-hidden flex flex-col data-[state=inactive]:hidden">
              <ScrollArea className="flex-1 pr-4">
                {isLoadingMetadata ? (
                  <div className="flex flex-col items-center justify-center py-8">
                    <Loader2 className="h-8 w-8 animate-spin mb-4 text-primary" />
                    <p className="text-center font-medium">Loading metadata options...</p>
                    <p className="text-center text-sm text-muted-foreground mt-1">
                      Searching music databases for the best match
                    </p>
                  </div>
                ) : metadataOptions.length === 0 ? (
                  <Card>
                    <CardContent className="py-4">
                      <p className="text-muted-foreground text-center">
                        No additional metadata found
                      </p>
                      <p className="text-xs text-muted-foreground text-center mt-2">
                        We'll use the information you provided in the previous
                        step
                      </p>
                    </CardContent>
                  </Card>
                ) : (
                  <RadioGroup 
                    value={String(metadataOptions.indexOf(selectedMetadata || metadataOptions[0]))} 
                    onValueChange={(value) => {
                      const index = parseInt(value);
                      setSelectedMetadata(metadataOptions[index] || null);
                    }}
                    className="space-y-4"
                  >
                    {metadataOptions.map((option, index) => (
                      <div key={option.id || index} className="flex items-start space-x-2">
                        <RadioGroupItem value={String(index)} id={`metadata-${index}`} className="mt-1" />
                        <div className="flex-1">
                          <Label 
                            htmlFor={`metadata-${index}`} 
                            className="flex flex-col space-y-1 cursor-pointer"
                          >
                            <Card className={`hover:border-primary ${selectedMetadata === option ? 'border-primary bg-primary/5' : ''}`}>
                              <CardContent className="p-3">
                                <div className="flex justify-between items-start">
                                  <div className="flex-1">
                                    <h4 className="font-medium text-sm">{option.title}</h4>
                                    <p className="text-sm text-muted-foreground">
                                      {option.artist}
                                      {option.album && ` • ${option.album}`}
                                    </p>
                                    {(option.year || option.genre || option.language) && (
                                      <div className="mt-1 flex flex-wrap gap-1">
                                        {option.year && (
                                          <span className="px-2 py-0.5 text-xs bg-secondary rounded-full">
                                            {option.year}
                                          </span>
                                        )}
                                        {option.genre && (
                                          <span className="px-2 py-0.5 text-xs bg-secondary rounded-full">
                                            {option.genre}
                                          </span>
                                        )}
                                        {option.language && (
                                          <span className="px-2 py-0.5 text-xs bg-secondary rounded-full">
                                            {option.language}
                                          </span>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                  {option.source && (
                                    <span className="text-xs bg-muted px-2 py-1 rounded text-muted-foreground">
                                      {option.source}
                                    </span>
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
            </TabsContent>

            <TabsContent value="lyrics" className="flex-1 overflow-hidden flex flex-col data-[state=inactive]:hidden">
              <ScrollArea className="flex-1 pr-4">
                {isLoadingLyrics ? (
                  <div className="flex flex-col items-center justify-center py-8">
                    <Loader2 className="h-8 w-8 animate-spin mb-4 text-primary" />
                    <p className="text-center font-medium">Loading lyrics options...</p>
                    <p className="text-center text-sm text-muted-foreground mt-1">
                      Searching for lyrics that match your song
                    </p>
                  </div>
                ) : lyricsOptions.length === 0 ? (
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
                    value={String(lyricsOptions.indexOf(selectedLyrics || lyricsOptions[0]))} 
                    onValueChange={(value) => {
                      const index = parseInt(value);
                      setSelectedLyrics(lyricsOptions[index] || null);
                    }}
                    className="space-y-4"
                  >
                    {lyricsOptions.map((option, index) => (
                      <div key={option.id || index} className="flex items-start space-x-2">
                        <RadioGroupItem value={String(index)} id={`lyrics-${index}`} className="mt-1" />
                        <div className="flex-1">
                          <Label 
                            htmlFor={`lyrics-${index}`} 
                            className="flex flex-col space-y-1 cursor-pointer"
                          >
                            <Card className={`hover:border-primary ${selectedLyrics === option ? 'border-primary bg-primary/5' : ''}`}>
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
            </TabsContent>
          </Tabs>
        )}

        <DialogFooter className="pt-2 flex-col sm:flex-row gap-2 sm:items-center">
          {isSubmitting ? null : (
            <>
              <Button
                variant="outline"
                onClick={onClose}
                className="sm:order-1 order-2"
              >
                Cancel
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={isSubmitting}
                className="sm:order-2 order-1"
              >
                Save & Add to Library
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}