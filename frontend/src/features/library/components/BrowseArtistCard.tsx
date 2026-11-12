import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Music, ArrowRight } from "lucide-react";
import { browseArtistOptions, useOpenAddSong } from "@/hooks/useOpenAddSong";

interface BrowseArtistCardProps {
  artistName: string;
  /** Their YouTube Music channel, when known: opened directly, no search. */
  youtubeMusicArtistId?: string | null;
}

export const BrowseArtistCard: React.FC<BrowseArtistCardProps> = ({
  artistName,
  youtubeMusicArtistId,
}) => {
  const openAddSong = useOpenAddSong();

  const handleClick = () => {
    openAddSong(
      browseArtistOptions({ name: artistName, youtubeMusicArtistId }),
    );
  };

  return (
    <Card
      className="group overflow-hidden relative hover:shadow-lg transition-shadow pt-0 pb-2 gap-0.5 border-dashed border-2 border-primary/40 hover:border-primary/80 cursor-pointer"
      onClick={handleClick}
    >
      <CardContent className="p-0 flex-1">
        <div className="flex flex-col">
          <div className="relative overflow-hidden flex items-center justify-center bg-primary/10 aspect-video w-full">
            <div className="flex flex-col items-center gap-2 text-primary/70 group-hover:text-primary transition-colors">
              <Music size={48} />
              <span className="text-xs font-medium uppercase tracking-wide">
                YouTube Music
              </span>
            </div>
          </div>
          <div className="p-3 flex-1">
            <h3 className="font-medium truncate text-primary/90">
              Find more from {artistName}
            </h3>
            <p className="text-sm opacity-75 flex items-center gap-1 mt-1">
              Browse on YouTube Music
              <ArrowRight size={14} />
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
