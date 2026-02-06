import React from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Music, ArrowRight } from "lucide-react";

interface BrowseArtistCardProps {
  artistName: string;
}

export const BrowseArtistCard: React.FC<BrowseArtistCardProps> = ({
  artistName,
}) => {
  const navigate = useNavigate();

  const handleClick = () => {
    navigate(`/add?q=${encodeURIComponent(artistName)}&browseArtist=true`);
  };

  return (
    <Card
      className="group overflow-hidden relative hover:shadow-lg transition-shadow pt-0 pb-2 gap-0.5 border-dashed border-2 border-orange-peel/40 hover:border-orange-peel/80 cursor-pointer"
      onClick={handleClick}
    >
      <CardContent className="p-0 flex-1">
        <div className="flex flex-col">
          <div className="relative overflow-hidden flex items-center justify-center bg-orange-peel/10 aspect-video w-full">
            <div className="flex flex-col items-center gap-2 text-orange-peel/70 group-hover:text-orange-peel transition-colors">
              <Music size={48} />
              <span className="text-xs font-medium uppercase tracking-wide">
                YouTube Music
              </span>
            </div>
          </div>
          <div className="p-3 flex-1">
            <h3 className="font-medium truncate text-orange-peel/90">
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
