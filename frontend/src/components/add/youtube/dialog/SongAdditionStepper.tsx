// frontend/src/components/upload/SongAdditionStepper.tsx
import { useState, useEffect } from "react";
import { toast } from "sonner";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Stepper,
  StepperIndicator,
  StepperItem,
  StepperSeparator,
  StepperTrigger,
} from "@/components/ui/stepper";

import {
  useMetadataSearch,
  useSaveMetadataMutation,
} from "@/hooks/useYoutube";

import { useLyricsSearch } from "@/hooks/useLyrics";

import type { LyricsOption, MetadataOption } from "@/components/forms";
import type { CreateSongResponse } from "@/hooks/useYoutube";

import {
  ConfirmDetailsStep,
  LyricsSelectionStep,
  MetadataSelectionStep,
} from "./steps";

// Types
interface SongAdditionStepperProps {
  isOpen: boolean;
  onClose: () => void;
  initialMetadata: {
    artist: string;
    title: string;
    album: string;
  };
  videoTitle: string;
  videoDuration: number;
  createdSong: CreateSongResponse;
  onComplete: () => void;
}

export function SongAdditionStepper({
  isOpen,
  onClose,
  initialMetadata,
  videoTitle,
  videoDuration,
  createdSong,
  onComplete,
}: SongAdditionStepperProps) {
  // Stepper state
  const [currentStep, setCurrentStep] = useState(1);
  const [confirmedMetadata, setConfirmedMetadata] = useState(initialMetadata);
  const [selectedLyrics, setSelectedLyrics] = useState<LyricsOption | null>(
    null
  );
  const [selectedMetadata, setSelectedMetadata] = useState<MetadataOption | null>(null);
  const [showSkipLyricsDialog, setShowSkipLyricsDialog] = useState(false);

  // API hooks
  const {
    data: lyricsOptions,
    loading: isLoadingLyrics,
    search: fetchLyrics,
  } = useLyricsSearch();

  const {
    data: metadataResponse,
    refetch: fetchMetadata,
    isPending: isLoadingMetadata,
  } = useMetadataSearch({
    enabled: false,
    queryKey: [
      "metadata",
      initialMetadata.artist,
      initialMetadata.title,
      initialMetadata.album,
    ],
  });

  // Extract metadata options from the response structure
  const metadataOptions = metadataResponse?.results || [];

  const saveMetadataMutation = useSaveMetadataMutation(createdSong.id, {
    onSuccess: () => {
      toast.success("Song added to library successfully!");
      onComplete();
      onClose();
    },
    onError: (error) => {
      toast.error(`Failed to save metadata: ${error.message}`);
    },
  });

  // Reset state when dialog opens/closes
  useEffect(() => {
    if (isOpen) {
      setCurrentStep(1);
      setConfirmedMetadata(initialMetadata);
      setSelectedLyrics(null);
      setSelectedMetadata(null);
      setMetadataSearchQuery({
        artist: initialMetadata.artist,
        title: initialMetadata.title,
        album: initialMetadata.album,
      });
    }
  }, [isOpen, initialMetadata]);

  // Auto-proceed from confirm step to lyrics step after API calls start
  useEffect(() => {
    if (currentStep === 2 && !isLoadingLyrics && lyricsOptions.length >= 0) {
      // Auto-select first lyrics option if available
      if (lyricsOptions.length > 0) {
        setSelectedLyrics(lyricsOptions[0]);
      }
    }
  }, [currentStep, isLoadingLyrics, lyricsOptions]);

  // Step 1: Confirm Details
  const handleStep1Continue = (newMetadata: {
    artist: string;
    title: string;
    album: string;
  }) => {
    setConfirmedMetadata(newMetadata);
    setMetadataSearchQuery({
      artist: newMetadata.artist,
      title: newMetadata.title,
      album: newMetadata.album,
    });
    // Start both API calls simultaneously and advance to lyrics step
    setCurrentStep(2);
    setTimeout(() => {
      fetchLyrics({
        artist: newMetadata.artist,
        title: newMetadata.title,
        album: newMetadata.album,
      });
      fetchMetadata();
    }, 100);
  };

  // Step 2: Lyrics Selection
  const handleLyricsConfirm = () => {
    // Auto-save lyrics immediately
    if (selectedLyrics) {
      toast.success("Lyrics saved successfully!");
    }
    setCurrentStep(3);
  };

  const handleLyricsSkip = () => {
    setShowSkipLyricsDialog(true);
  };

  const confirmSkipLyrics = () => {
    setSelectedLyrics(null);
    setCurrentStep(3);
    setShowSkipLyricsDialog(false);
  };

  const handleLyricsResearch = (query: {
    artist: string;
    title: string;
    album: string;
  }) => {
    fetchLyrics(query);
  };

  // Step 3: Metadata Selection
  const handleMetadataConfirm = () => {
    saveMetadataMutation.mutate({
      title: selectedMetadata?.title || confirmedMetadata.title,
      artist: selectedMetadata?.artist || confirmedMetadata.artist,
      album: selectedMetadata?.album || confirmedMetadata.album,
      lyrics: selectedLyrics?.plainLyrics,
      syncedLyrics: selectedLyrics?.syncedLyrics,
      metadataId: selectedMetadata?.metadataId,
    });
  };

  const handleMetadataSkip = () => {
    // Skip metadata completely - save with just lyrics
    saveMetadataMutation.mutate({
      title: confirmedMetadata.title,
      artist: confirmedMetadata.artist,
      album: confirmedMetadata.album,
      lyrics: selectedLyrics?.plainLyrics,
      syncedLyrics: selectedLyrics?.syncedLyrics,
    });
  };

  const handleMetadataResearch = (query: { artist: string; title: string; album: string }) => {
    setMetadataSearchQuery(query);
    fetchMetadata();
  };

  // Render step content
  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return (
          <ConfirmDetailsStep
            initialMetadata={initialMetadata}
            videoTitle={videoTitle}
            onContinue={handleStep1Continue}
          />
        );

      case 2:
        return (
          <LyricsSelectionStep
            lyricsOptions={lyricsOptions}
            selectedLyrics={selectedLyrics}
            videoDuration={videoDuration}
            isSearching={isLoadingLyrics}
            initialMetadata={confirmedMetadata}
            onLyricsSelect={(lyrics) => setSelectedLyrics(lyrics)}
            onConfirm={handleLyricsConfirm}
            onSkip={handleLyricsSkip}
            onResearch={handleLyricsResearch}
          />
        );

      case 3:
        return (
          <MetadataSelectionStep
            metadataOptions={metadataOptions}
            selectedMetadata={selectedMetadata}
            isSearching={isLoadingMetadata}
            initialMetadata={confirmedMetadata}
            onMetadataSelect={(metadata) => setSelectedMetadata(metadata)}
            onConfirm={handleMetadataConfirm}
            onSkip={handleMetadataSkip}
            onResearch={handleMetadataResearch}
          />
        );

      default:
        return null;
    }
  };

  const steps = [1, 2, 3];
  const stepLabels = ["Confirm", "Lyrics", "Metadata"];

  return (
    <>
      <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
        <DialogContent className="sm:max-w-[700px] max-h-[90vh] flex flex-col">
          <DialogHeader className="flex-shrink-0">
            <DialogTitle>Add Song to Library</DialogTitle>
            <DialogDescription>
              Adding: <strong>{videoTitle}</strong>
            </DialogDescription>
          </DialogHeader>

          <div className="container mx-auto max-w-xl flex-shrink-0">
            {/* Stepper */}
            <Stepper value={currentStep} className="w-full pt-4 px-3">
              {steps.map((step, index) => (
                <StepperItem
                  key={step}
                  step={step}
                  className={index < steps.length - 1 ? "flex-1" : ""}
                >
                  <StepperTrigger className="flex flex-col items-center gap-2">
                    <StepperIndicator />
                    <div className="text-xs h-4">{stepLabels[index]}</div>
                  </StepperTrigger>
                  {index < steps.length - 1 && (
                    <StepperSeparator className="mb-5" />
                  )}
                </StepperItem>
              ))}
            </Stepper>
          </div>

          {/* Step content */}
          <div className="flex-1">
            {renderStepContent()}
          </div>
        </DialogContent>
      </Dialog>

      {/* Skip Lyrics Confirmation Dialog */}
      <AlertDialog
        open={showSkipLyricsDialog}
        onOpenChange={setShowSkipLyricsDialog}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Skip Lyrics?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you've got this one memorized? 🎤
              <br />
              You can always add lyrics later from the song details page.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmSkipLyrics}>
              Yes, Skip Lyrics
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
