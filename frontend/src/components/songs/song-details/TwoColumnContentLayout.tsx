import React from "react";
import { Song } from "@/types/Song";
import { SongLyricsSection } from "./SongLyricsSection";
import { SecondaryActionsPanel } from "./SecondaryActionsPanel";

interface TwoColumnContentLayoutProps {
  song: Song;
}

export const TwoColumnContentLayout: React.FC<TwoColumnContentLayoutProps> = ({
  song,
}) => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-6 lg:gap-8 mt-6">
      {/* Left Column: Lyrics Section */}
      <div className="min-w-0">
        <SongLyricsSection song={song} />
      </div>

      {/* Right Column: Secondary Actions */}
      <div className="flex flex-col">
        <SecondaryActionsPanel song={song} />
      </div>
    </div>
  );
};
