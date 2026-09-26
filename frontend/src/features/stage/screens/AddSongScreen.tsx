/**
 * AddSongScreen - the add flow, mirrored onto the TV.
 *
 * `SongSearchContainer` already imports nothing from the router and already
 * takes its query as a prop, so this screen is a back button and that component.
 *
 * The one rule specific to the stage: hand back on *submit*, not on completion.
 * Download plus Demucs runs for minutes, and a TV that sits on a spinner for
 * that long is a dead cabinet — the song surfaces in the library when it lands.
 */

import React from "react";
import { ChevronLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SongSearchContainer } from "@/features/songs/components/shared/SongSearchContainer";
import { useStageShell } from "../StageShellContext";

interface AddSongScreenProps {
  query?: string;
  browseArtist?: boolean;
}

const AddSongScreen: React.FC<AddSongScreenProps> = ({
  query,
  browseArtist,
}) => {
  const shell = useStageShell();

  return (
    <div className="flex h-full w-full flex-col overflow-hidden">
      <div className="shrink-0 px-6 pt-4">
        <Button
          variant="ghost"
          onClick={() => shell?.back()}
          className="text-foreground/60 hover:text-foreground"
        >
          <ChevronLeft className="mr-1 size-5" />
          Back to songs
        </Button>
      </div>

      <div className="min-h-0 flex-1 overflow-auto p-6">
        <div className="container mx-auto space-y-6">
          <SongSearchContainer
            initialQuery={query ?? ""}
            autoBrowseArtist={browseArtist ?? false}
            onSubmitted={() => shell?.openSelect()}
          />
        </div>
      </div>
    </div>
  );
};

export default AddSongScreen;
