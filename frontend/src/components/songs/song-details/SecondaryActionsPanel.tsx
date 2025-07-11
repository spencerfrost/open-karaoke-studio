import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Edit,
  FileText,
  MoreHorizontal,
  Download,
  Share,
  Trash2,
} from "lucide-react";
import { Song } from "@/types/Song";
import { toast } from "sonner";
import { LyricsFetchDialog } from "@/components/lyrics";

interface SecondaryActionsPanelProps {
  song: Song;
}

export const SecondaryActionsPanel: React.FC<SecondaryActionsPanelProps> = ({
  song,
}) => {
  const [isMoreActionsOpen, setIsMoreActionsOpen] = useState(false);
  const [isLyricsFetchDialogOpen, setIsLyricsFetchDialogOpen] = useState(false);

  const handleEditMetadata = () => {
    // For 016E: Show "Coming Soon" message
    toast.info("Metadata editing coming soon!");
    // For 016F: Open metadata editing interface
  };

  const handleEditLyrics = () => {
    setIsLyricsFetchDialogOpen(true);
  };

  const handleLyricsFetched = (results: LyricsResult[]) => {
    console.log("Lyrics fetched:", results);
  };

  const handleLyricsSelected = (selectedLyrics: LyricsResult) => {
    console.log("Lyrics selected:", selectedLyrics);
    toast.success(
      `Lyrics selected: ${selectedLyrics.trackName} by ${selectedLyrics.artistName}`
    );
    setIsLyricsFetchDialogOpen(false);
  };

  const handleDownload = () => {
    toast.info("Download feature coming soon!");
    setIsMoreActionsOpen(false);
  };

  const handleShare = () => {
    toast.info("Share feature coming soon!");
    setIsMoreActionsOpen(false);
  };

  const handleRemove = () => {
    toast.info("Remove from library feature coming soon!");
    setIsMoreActionsOpen(false);
  };

  // Suppress unused variable warning for now
  console.log("SecondaryActionsPanel for song:", song.id);

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-muted-foreground mb-4">
        Actions
      </h3>

      <div className="flex flex-col gap-2">
        <Button
          variant="outline"
          onClick={handleEditMetadata}
          className="w-full justify-start gap-2"
          size="sm"
        >
          <Edit size={14} />
          Edit Metadata
        </Button>

        <Button
          variant="outline"
          onClick={handleEditLyrics}
          className="w-full justify-start gap-2"
          size="sm"
        >
          <FileText size={14} />
          Edit Lyrics
        </Button>

        <Popover open={isMoreActionsOpen} onOpenChange={setIsMoreActionsOpen}>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              className="w-full justify-start gap-2"
              size="sm"
            >
              <MoreHorizontal size={14} />
              More Actions
            </Button>
          </PopoverTrigger>
          <PopoverContent align="start" className="w-48 p-2">
            <div className="flex flex-col gap-1">
              <Button
                variant="ghost"
                onClick={handleDownload}
                className="w-full justify-start gap-2"
                size="sm"
              >
                <Download size={14} />
                Download Song
              </Button>
              <Button
                variant="ghost"
                onClick={handleShare}
                className="w-full justify-start gap-2"
                size="sm"
              >
                <Share size={14} />
                Share Song
              </Button>
              <Button
                variant="ghost"
                onClick={handleRemove}
                className="w-full justify-start gap-2 text-destructive hover:text-destructive"
                size="sm"
              >
                <Trash2 size={14} />
                Remove from Library
              </Button>
            </div>
          </PopoverContent>
        </Popover>
      </div>

      {/* Lyrics Fetch Dialog */}
      <LyricsFetchDialog
        isOpen={isLyricsFetchDialogOpen}
        onClose={() => setIsLyricsFetchDialogOpen(false)}
        song={song}
        onLyricsFetched={handleLyricsFetched}
        onLyricsSelected={handleLyricsSelected}
      />
    </div>
  );
};
