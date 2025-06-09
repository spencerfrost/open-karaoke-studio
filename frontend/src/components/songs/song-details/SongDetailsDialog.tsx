import React, { useEffect, useState } from "react";
import { Song } from "@/types/Song";
import { ArtworkDisplay } from "./ArtworkDisplay";
import { PrimarySongDetails } from "./PrimarySongDetails";
import { PrimaryActionsSection } from "./PrimaryActionsSection";
import { TwoColumnContentLayout } from "./TwoColumnContentLayout";
import { MetadataEditContent } from "./MetadataEditContent";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

interface SongDetailsDialogProps {
  song: Song;
  isOpen: boolean;
  onClose: () => void;
  className?: string;
}

type DialogView = 'main' | 'edit-metadata';

export const SongDetailsDialog: React.FC<SongDetailsDialogProps> = ({
  song,
  isOpen,
  onClose,
  className = "",
}) => {
  const [currentView, setCurrentView] = useState<DialogView>('main');

  // Close audio when dialog closes
  useEffect(() => {
    if (!isOpen) {
      // Stop any playing audio when dialog closes
      const audioElements = document.querySelectorAll("audio");
      audioElements.forEach((audio) => {
        audio.pause();
        audio.currentTime = 0;
      });
      // Reset view when dialog closes
      setCurrentView('main');
    }
  }, [isOpen]);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        if (currentView === 'edit-metadata') {
          setCurrentView('main');
        } else {
          onClose();
        }
      }
    };

    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      return () => document.removeEventListener("keydown", handleEscape);
    }
  }, [isOpen, onClose, currentView]);

  const handleEditMetadata = () => {
    setCurrentView('edit-metadata');
  };

  const handleBackToMain = () => {
    setCurrentView('main');
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        className={cn(
          // Mobile: full screen
          "w-screen h-screen max-w-none max-h-none rounded-none",
          // Desktop: large dialog
          "md:w-[90vw] md:h-[90vh] md:max-w-6xl md:max-h-[90vh] md:rounded-lg",
          "overflow-y-auto p-0",
          className
        )}
      >
        <div className="p-8 space-y-8">
          {currentView === 'main' ? (
            <>
              {/* Main content grid - Cover art and primary details */}
              <div className="grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-8">
                {/* Left column - Cover art */}
                <div className="flex justify-center lg:justify-start">
                  <ArtworkDisplay
                    song={song}
                    size="large"
                    className="w-full max-w-[300px]"
                    showFallback={true}
                  />
                </div>

                {/* Right column - Primary song details */}
                <div className="min-w-0 space-y-6">
                  <PrimarySongDetails song={song} />
                </div>
              </div>

              {/* Primary Actions Section - Prominent placement below song details */}
              <PrimaryActionsSection 
                song={song} 
                onClose={onClose} 
                onEditMetadata={handleEditMetadata} 
              />

              {/* Two-Column Layout: Lyrics + Secondary Actions */}
              <TwoColumnContentLayout song={song} />
            </>
          ) : (
            /* Metadata Editing View */
            <MetadataEditContent 
              song={song}
              onBack={handleBackToMain}
            />
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};
