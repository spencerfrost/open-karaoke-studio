/**
 * AddSongScreen - the add flow, mirrored onto the TV.
 *
 * The same screens as the phone's /add; the shell keeps their stack, and
 * `shell.back()` walks it (album → artist → search → song select).
 *
 * Adding a song stays on this screen, so a guest can add several and go back
 * when done. Each song shows up in the wheel when it's ready.
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
        <AddSongFlow step={step} onExit={() => shell?.back()} />
      </div>
      <StageNowPlaying />
    </div>
  );
};

export default AddSongScreen;
