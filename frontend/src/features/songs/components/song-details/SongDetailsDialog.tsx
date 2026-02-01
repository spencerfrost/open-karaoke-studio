import React, { useEffect, useState } from "react";
import { Song } from "@/types/Song";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { OverviewTab, DetailsTab, LyricsTab, AudioTab } from "./tabs";
import { MetadataEditContent } from "./MetadataEditContent";
import { cn } from "@/lib/utils";
import { Info, FileText, Music2, Settings } from "lucide-react";

interface SongDetailsDialogProps {
  song: Song;
  isOpen: boolean;
  onClose: () => void;
  className?: string;
}

type DialogView = "tabs" | "itunes-search";
type TabValue = "overview" | "details" | "lyrics" | "audio";

export const SongDetailsDialog: React.FC<SongDetailsDialogProps> = ({
  song,
  isOpen,
  onClose,
  className = "",
}) => {
  const [currentView, setCurrentView] = useState<DialogView>("tabs");
  const [activeTab, setActiveTab] = useState<TabValue>("overview");

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
      setCurrentView("tabs");
      setActiveTab("overview");
    }
  }, [isOpen]);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        if (currentView === "itunes-search") {
          setCurrentView("tabs");
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

  const handleLaunchItunesSearch = () => {
    setCurrentView("itunes-search");
  };

  const handleBackFromItunesSearch = () => {
    setCurrentView("tabs");
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        className={cn(
          // Mobile: full screen
          "w-screen h-screen max-w-none max-h-none rounded-none",
          // Desktop: large dialog
          "md:w-[90vw] md:h-[90vh] md:max-w-5xl md:max-h-[90vh] md:rounded-lg",
          "overflow-hidden p-0",
          className,
        )}
      >
        {currentView === "tabs" ? (
          <Tabs
            value={activeTab}
            onValueChange={(value) => setActiveTab(value as TabValue)}
            className="flex flex-col h-full"
          >
            <div className="border-b">
              <TabsList className="w-full grid grid-cols-4 p-0 h-auto bg-transparent rounded-none">
                <TabsTrigger
                  value="overview"
                  className="flex items-center justify-center gap-2 rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-muted/50 py-3 px-2 transition-colors"
                >
                  <Info size={18} className="text-muted-foreground" />
                  <span className="hidden sm:inline text-sm font-medium">
                    Overview
                  </span>
                </TabsTrigger>
                <TabsTrigger
                  value="details"
                  className="flex items-center justify-center gap-2 rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-muted/50 py-3 px-2 transition-colors"
                >
                  <Settings size={18} className="text-muted-foreground" />
                  <span className="hidden sm:inline text-sm font-medium">
                    Details
                  </span>
                </TabsTrigger>
                <TabsTrigger
                  value="lyrics"
                  className="flex items-center justify-center gap-2 rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-muted/50 py-3 px-2 transition-colors"
                >
                  <FileText size={18} className="text-muted-foreground" />
                  <span className="hidden sm:inline text-sm font-medium">
                    Lyrics
                  </span>
                </TabsTrigger>
                <TabsTrigger
                  value="audio"
                  className="flex items-center justify-center gap-2 rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-muted/50 py-3 px-2 transition-colors"
                >
                  <Music2 size={18} className="text-muted-foreground" />
                  <span className="hidden sm:inline text-sm font-medium">
                    Audio
                  </span>
                </TabsTrigger>
              </TabsList>
            </div>

            <div className="flex-1 overflow-y-auto">
              <div className="p-6 space-y-6">
                <TabsContent
                  value="overview"
                  className="mt-0 data-[state=inactive]:hidden"
                >
                  <OverviewTab
                    song={song}
                    onClose={onClose}
                    onSongDeleted={onClose}
                  />
                </TabsContent>

                <TabsContent
                  value="details"
                  className="mt-0 data-[state=inactive]:hidden"
                >
                  <DetailsTab
                    song={song}
                    onLaunchItunesSearch={handleLaunchItunesSearch}
                  />
                </TabsContent>

                <TabsContent
                  value="lyrics"
                  className="mt-0 data-[state=inactive]:hidden"
                >
                  <LyricsTab song={song} />
                </TabsContent>

                <TabsContent
                  value="audio"
                  className="mt-0 data-[state=inactive]:hidden"
                >
                  <AudioTab song={song} />
                </TabsContent>
              </div>
            </div>
          </Tabs>
        ) : (
          /* iTunes Search View */
          <div className="p-6 h-full overflow-y-auto">
            <MetadataEditContent
              song={song}
              onBack={handleBackFromItunesSearch}
            />
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};
