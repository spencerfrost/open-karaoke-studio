/**
 * SongSelectScreen - the stage's resting screen: pick something to sing.
 *
 * The same library the phone browses, framed for a TV across the room: one slim
 * bar at the top for the two things that are not "pick a song" (back to the
 * song that is playing, and leaving stage mode), and a floating add button for
 * the cold start — "I want a song that isn't here and I'm not searching yet."
 */

import React from "react";
import { LogOut, Plus, Undo2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { LibraryScreen } from "@/features/library";
import SessionInfoDisplay from "@/components/session/SessionInfoDisplay";
import { useStageShell } from "../StageShellContext";

interface SongSelectScreenProps {
  expandArtist?: string;
  /** Whether there is a song loaded to go back to. */
  hasCurrentSong: boolean;
  onExitStage: () => void;
}

const SongSelectScreen: React.FC<SongSelectScreenProps> = ({
  expandArtist,
  hasCurrentSong,
  onExitStage,
}) => {
  const shell = useStageShell();

  return (
    <div className="flex h-full w-full flex-col overflow-hidden">
      <div className="flex shrink-0 items-center justify-between gap-4 px-6 pt-4">
        {/* The one back affordance stage mode allows, and only when there is
            something to go back to. */}
        {hasCurrentSong ? (
          <Button
            variant="ghost"
            onClick={() => shell?.openPerformance()}
            className="text-foreground/60 hover:text-foreground"
          >
            <Undo2 className="mr-2 size-5" />
            Back to the song
          </Button>
        ) : (
          <span />
        )}

        <div className="flex items-center gap-2">
          <SessionInfoDisplay />
          {/* Deliberately quiet: the mouse lives on the mic stand, and nobody
              walking up to sing should end the night by brushing this. */}
          <Button
            variant="ghost"
            size="sm"
            onClick={onExitStage}
            aria-label="Exit stage mode"
            className="text-foreground/35 hover:text-foreground"
          >
            <LogOut className="mr-2 size-4" />
            Exit stage
          </Button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-auto px-6">
        <LibraryScreen
          expandArtist={expandArtist}
          searchPlaceholder="What do you want to sing?"
        />
      </div>

      <Button
        variant="accent"
        size="lg"
        onClick={() => shell?.openAdd()}
        className="absolute bottom-8 right-8 z-10 size-16 rounded-full shadow-xl"
        aria-label="Add a song to the library"
      >
        <Plus className="size-8" />
      </Button>
    </div>
  );
};

/**
 * Memoized, and given only stable props by the shell. It stays mounted behind
 * the other screens, so without this every transition would re-render the whole
 * library — ~600 artist rows and the recently-added grid — on the way past.
 */
export default React.memo(SongSelectScreen);
