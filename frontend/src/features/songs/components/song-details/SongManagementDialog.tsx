import React, { useEffect } from "react";
import { Song } from "@/types/Song";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DetailsTab, LyricsTab } from "./tabs";
import { ActionsTab } from "./tabs/ActionsTab";
import { SongManagementHeader } from "./SongManagementHeader";
import { cn } from "@/lib/utils";
import { useSongs } from "@/hooks/api/useSongs";
import { useProcessingIndicators } from "@/stores/processingIndicatorsStore";
import { Settings, FileText, Wrench } from "lucide-react";

interface SongManagementDialogProps {
  song: Song;
  isOpen: boolean;
  onClose: () => void;
  className?: string;
}

export const SongManagementDialog: React.FC<SongManagementDialogProps> = ({
  song,
  isOpen,
  onClose,
  className = "",
}) => {
  const { useSong } = useSongs();
  const processingStatus = useProcessingIndicators((state) =>
    state.getStatus(song.id),
  );
  const { data: liveSong } = useSong(song.id, {
    enabled: isOpen,
    refetchInterval:
      isOpen && processingStatus?.status === "processing" ? 3000 : false,
  });
  const currentSong = liveSong ?? song;

  useEffect(() => {
    if (!isOpen) {
      document.querySelectorAll("audio").forEach((audio) => {
        audio.pause();
        audio.currentTime = 0;
      });
    }
  }, [isOpen]);

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        className={cn(
          "w-screen h-screen max-w-none max-h-none rounded-none",
          "md:w-[90vw] md:h-[90vh] md:max-w-5xl md:max-h-[90vh] md:rounded-lg",
          "overflow-hidden p-0 flex flex-col",
          className,
        )}
      >
        <div className="px-6 py-4 border-b flex-shrink-0">
          <SongManagementHeader song={currentSong} onDeleted={onClose} />
        </div>

        <Tabs defaultValue="details" className="flex flex-col flex-1 min-h-0">
          <div className="border-b flex-shrink-0">
            <TabsList className="w-full grid grid-cols-3 p-0 h-auto bg-transparent rounded-none">
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
                value="actions"
                className="flex items-center justify-center gap-2 rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-muted/50 py-3 px-2 transition-colors"
              >
                <Wrench size={18} className="text-muted-foreground" />
                <span className="hidden sm:inline text-sm font-medium">
                  Actions
                </span>
              </TabsTrigger>
            </TabsList>
          </div>

          <div className="flex-1 overflow-y-auto">
            <div className="p-6 space-y-6">
              <TabsContent
                value="details"
                className="mt-0 data-[state=inactive]:hidden"
              >
                <DetailsTab song={currentSong} />
              </TabsContent>
              <TabsContent
                value="lyrics"
                className="mt-0 data-[state=inactive]:hidden"
              >
                <LyricsTab song={currentSong} />
              </TabsContent>
              <TabsContent
                value="actions"
                className="mt-0 data-[state=inactive]:hidden"
              >
                <ActionsTab song={currentSong} onDone={onClose} />
              </TabsContent>
            </div>
          </div>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
};
