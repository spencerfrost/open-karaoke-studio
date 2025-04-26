import React, { useState } from "react";
import { Button } from "../ui/button";
import { Dialog, DialogContent } from "../ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";
import { Pencil } from "lucide-react";
import { Song } from "../../types/Song";
import vintageTheme from "../../utils/theme";
import { updateSongMetadata } from "../../services/songService";
import MetadataEditorTab from "./MetadataEditorTab";
import MusicBrainzSearchTab from "./MusicBrainzSearchTab";

interface MetadataEditorProps {
  song: Song;
  onSongUpdated: (updatedSong: Song) => void;
  buttonClassName?: string;
}

const MetadataEditor: React.FC<MetadataEditorProps> = ({
  song,
  onSongUpdated,
  buttonClassName = "",
}) => {
  const [open, setOpen] = useState(false);
  const [activeTab, setActiveTab] = useState("edit");
  const colors = vintageTheme.colors;

  const handleSaveMetadata = async (metadata: Partial<Song>) => {
    try {
      const updatedSong = await updateSongMetadata(song.id, metadata);
      onSongUpdated(updatedSong.data as Song);
      setOpen(false);
    } catch (error) {
      console.error("Failed to update metadata:", error);
    }
  };

  const handleSelectMusicBrainzResult = (result: Partial<Song>) => {
    // Save the selected result to the metadata but preserve existing lyrics
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

  return (
    <>
      {/* Edit Button */}
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setOpen(true)}
        className={`text-xs flex items-center gap-1 px-2 ${buttonClassName}`}
        style={{ color: colors.darkCyan }}
      >
        <Pencil size={14} />
        Edit Info
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
        </DialogContent>
      </Dialog>
    </>
  );
};

export default MetadataEditor;
