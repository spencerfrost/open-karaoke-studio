/**
 * AddSongScreen - the add flow, mirrored onto the TV.
 *
 * The same screens as the phone's /add; the shell keeps their stack, and
 * `shell.back()` walks it (album → artist → search → song select).
 *
 * The one rule specific to the stage: hand back on *submit*, not on completion.
 * Download plus Demucs runs for minutes, and a TV that sits on a spinner for
 * that long is a dead cabinet — the song surfaces in the library when it lands.
 */

import React from "react";
import { AddSongFlow } from "@/features/songs/components/add-song/AddSongFlow";
import type { AddFlowStep } from "@/hooks/useAddFlowNavigation";
import StageNowPlaying from "../components/StageNowPlaying";
import { useStageShell } from "../StageShellContext";

interface AddSongScreenProps {
  step: AddFlowStep;
}

const AddSongScreen: React.FC<AddSongScreenProps> = ({ step }) => {
  const shell = useStageShell();

  return (
    <div className="flex h-full w-full flex-col overflow-hidden">
      <div className="min-h-0 flex-1 overflow-auto pt-4">
        <AddSongFlow
          step={step}
          onExit={() => shell?.back()}
          onAdded={() => shell?.openSelect()}
        />
      </div>
      <StageNowPlaying />
    </div>
  );
};

export default AddSongScreen;
