import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Edit, FileText, Trash2 } from "lucide-react";
import { Song } from "@/types/Song";
import { toast } from "sonner";
import { LyricsFetchDialog } from "@/components/LyricsFetchDialog";
import { useSongs } from "@/hooks/api/useSongs";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

interface SecondaryActionsPanelProps {
  song: Song;
}

export const SecondaryActionsPanel: React.FC<SecondaryActionsPanelProps> = ({
  song,
}) => {
  const [isLyricsFetchDialogOpen, setIsLyricsFetchDialogOpen] = useState(false);
  const { useDeleteSong } = useSongs();
  const deleteSongMutation = useDeleteSong();

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
      `Lyrics selected: ${selectedLyrics.trackName} by ${selectedLyrics.artistName}`,
    );
    setIsLyricsFetchDialogOpen(false);
  };

  const handleRemove = () => {
    deleteSongMutation.mutate({ id: song.id });
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

        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button
              variant="outline"
              className="w-full justify-start gap-2 text-destructive hover:text-destructive"
              size="sm"
            >
              <Trash2 size={14} />
              Remove from Library
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Are you sure?</AlertDialogTitle>
              <AlertDialogDescription>
                This action cannot be undone. This will permanently delete the
                song and all its data.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleRemove}>
                Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
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
