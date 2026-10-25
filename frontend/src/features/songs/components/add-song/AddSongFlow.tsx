/**
 * AddSongFlow - the add-song screens, on a phone or on the stage.
 *
 * The caller says which screen (`step`) and how to leave; everything else is
 * shared. It stays mounted while the screens change, so this page's
 * submissions and the preview player carry from one screen to the next.
 */

import React from "react";
import type { AddFlowStep } from "@/hooks/useAddFlowNavigation";
import { AddSongProvider } from "./AddSongProvider";
import { AlbumScreen } from "./AlbumScreen";
import { ArtistScreen } from "./ArtistScreen";
import { PreviewBar, PreviewProvider } from "./PreviewPlayer";
import { SearchScreen } from "./SearchScreen";

interface AddSongFlowProps {
  step: AddFlowStep;
  /** Leave the flow, back to the songbook. */
  onExit: () => void;
  /** Called after a song is added. */
  onAdded?: () => void;
}

export const AddSongFlow: React.FC<AddSongFlowProps> = ({
  step,
  onExit,
  onAdded,
}) => (
  <AddSongProvider onAdded={onAdded}>
    <PreviewProvider>
      <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 px-4 pt-2 pb-4 sm:px-6">
        {step.kind === "search" && <SearchScreen step={step} onExit={onExit} />}
        {step.kind === "artist" && (
          <ArtistScreen key={step.browseId} step={step} />
        )}
        {step.kind === "album" && (
          <AlbumScreen key={step.browseId} step={step} />
        )}
        <PreviewBar />
      </div>
    </PreviewProvider>
  </AddSongProvider>
);
