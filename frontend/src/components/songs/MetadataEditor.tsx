import React, { useState } from "react";
import { Button } from "../ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../ui/dialog";
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
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState("edit");
  const colors = vintageTheme.colors;

  const handleSaveMetadata = async (metadata: Partial<Song>) => {
    try {
      setIsSubmitting(true);
      const updatedSong = await updateSongMetadata(song.id, metadata);
      onSongUpdated(updatedSong);
      setOpen(false);
    } catch (error) {
      console.error("Failed to update metadata:", error);
      // TODO: Show error toast/message
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSelectMusicBrainzResult = (result: Partial<Song>) => {
    // Switch to edit tab to let user review and save the changes
    setActiveTab("edit");
    // The metadata will be saved when user clicks Save in the edit tab
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
        <DialogContent className="sm:max-w-[625px] min-h-1/3 bg-foreground text-background">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="pt-0">
            <TabsList className="w-full p-0">
              <TabsTrigger
                value="edit"
                className={`w-50 ${
                  activeTab === "edit"
                    ? "text-foreground"
                    : "text-background border border-border"
                }`}
              >
                Edit Metadata
              </TabsTrigger>
              <TabsTrigger
                value="search"
                className={`w-50 ${
                  activeTab === "search"
                    ? "text-foreground"
                    : "text-background border border-border"
                }`}
              >
                MusicBrainz Search
              </TabsTrigger>
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
