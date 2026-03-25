import React, { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { useSongs } from "@/hooks/api/useSongs";
import { SongArtwork } from "./SongArtwork";
import { SongInfo } from "./SongInfo";
import { PerformerSongDrawer } from "./PerformerSongDrawer";
import { SongCardProps } from "./SongCard.types";

export const PerformerSongCard: React.FC<SongCardProps> = ({ song, showArtist = true }) => {
  const { getArtworkUrl } = useSongs();
  const artworkUrl = getArtworkUrl(song, "medium");
  const [drawerOpen, setDrawerOpen] = useState(false);

  const handleCardClick = () => {
    setDrawerOpen(true);
  };

  // No-op for artwork click — the card-level click handles it
  const handleArtworkClick = (e?: React.MouseEvent) => {
    e?.stopPropagation();
    setDrawerOpen(true);
  };

  return (
    <>
      <Card
        className="group overflow-hidden relative hover:shadow-lg transition-shadow pt-0 pb-2 gap-0.5 cursor-pointer active:scale-[0.98] transition-transform"
        onClick={handleCardClick}
      >
        <CardContent className="p-0 flex-1">
          <div className="flex flex-col">
            <SongArtwork
              song={song}
              artworkUrl={artworkUrl}
              showSyncedBadge={true}
              onPlay={handleArtworkClick}
              showPlayButton={false}
            />
            <SongInfo song={song} showArtist={showArtist} />
          </div>
        </CardContent>
      </Card>

      <PerformerSongDrawer
        song={song}
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      />
    </>
  );
};
