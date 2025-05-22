import React, { useState } from "react";
import { Button } from "../ui/button";
import { Dialog, DialogContent } from "../ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";
import { Pencil } from "lucide-react";
import { Song } from "../../types/Song";
import { useSongs } from "../../hooks/useSongs";
import MetadataEditorTab from "./MetadataEditorTab";
import MusicBrainzSearchTab from "./MusicBrainzSearchTab";

interface MetadataEditorProps {
  song: Song;
  onSongUpdated: (updatedSong: Song) => void;
  buttonClassName?: string;
  icon?: boolean;
}

const MetadataEditor: React.FC<MetadataEditorProps> = ({
  song,
  onSongUpdated,
  buttonClassName = "",
  icon = false,
}) => {
  const [open, setOpen] = useState(false);
  const [activeTab, setActiveTab] = useState("edit");
  const { useUpdateSongMetadata, useDeleteSong } = useSongs();
  
  const updateMetadata = useUpdateSongMetadata();
  const deleteSong = useDeleteSong();

  const handleSaveMetadata = async (metadata: Partial<Song>) => {
    try {
      const result = await updateMetadata.mutateAsync({ 
        id: song.id, 
        ...metadata 
      });
      
      if (result) {
        onSongUpdated(result);
      }
      setOpen(false);
    } catch (error) {
      console.error("Failed to update metadata:", error);
    }
  };

  const handleSelectMusicBrainzResult = (result: Partial<Song>) => {
    const metadataToSave: Partial<Song> = {
      title: result.title,
      artist: result.artist,
      album: result.album,
      year: result.year,
      genre: result.genre,
      language: result.language,
      coverArt: result.coverArt,
      lyrics: song.lyrics,
      syncedLyrics: song.syncedLyrics,
    };
    handleSaveMetadata(metadataToSave);
  };

  const handleDeleteSong = async () => {
    if (
      window.confirm(
        "Are you sure you want to delete this song? This action cannot be undone."
      )
    ) {
      try {
        await deleteSong.mutateAsync(song.id);
        setOpen(false);
        alert("Song deleted successfully.");
      } catch (error) {
        console.error("Failed to delete song:", error);
        alert("Failed to delete the song. Please try again.");
      }
    }
  };

  return (
    <>
      {/* Edit Button */}
      <Button
        variant="ghost"
        onClick={() => setOpen(true)}
        className={`text-xs flex items-center gap-1 text-accent ${buttonClassName}`}
      >
        <Pencil size={14} />
        {icon ? null : "Edit Metadata"}
      </Button>

      {/* Dialog */}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-[625px] min-h-1/3">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="w-full p-0">
              <TabsTrigger value="edit">Edit Metadata</TabsTrigger>
              <TabsTrigger value="search">MusicBrainz Search</TabsTrigger>
            </TabsList>
            <TabsContent value="edit">
              <MetadataEditorTab song={song} onSave={handleSaveMetadata} />
            </TabsContent>
            <TabsContent value="search">
              <MusicBrainzSearchTab
                song={song}
                onSelectResult={handleSelectMusicBrainzResult}
              />
            </TabsContent>
          </Tabs>
          <div className="flex justify-end mt-4">
            <Button 
              variant="destructive" 
              onClick={handleDeleteSong}
              disabled={deleteSong.isPending}
            >
              {deleteSong.isPending ? "Deleting..." : "Delete Song"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default MetadataEditor;
