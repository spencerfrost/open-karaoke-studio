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
import {
  LyricsOption,
  MetadataOption,
} from "@/hooks/useYoutube";
import { MetadataTab } from "./MetadataTab";
import { LyricsTab } from "./LyricsTab";

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
              <MetadataTab 
                options={metadataOptions}
                selectedOption={selectedMetadata}
                onSelectionChange={setSelectedMetadata}
                isLoading={isLoadingMetadata}
              />
            </TabsContent>

            <TabsContent value="lyrics" className="flex-1 overflow-hidden flex flex-col data-[state=inactive]:hidden">
              <LyricsTab 
                options={lyricsOptions}
                selectedOption={selectedLyrics}
                onSelectionChange={setSelectedLyrics}
                isLoading={isLoadingLyrics}
              />
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