import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { User } from "lucide-react";
import { YoutubeMusicArtistSearchResult } from "@/types/Youtube";

interface ArtistResultCardProps {
  result: YoutubeMusicArtistSearchResult;
  onArtistClick: (artistId: string, artistName: string) => void;
}

export const ArtistResultCard: React.FC<ArtistResultCardProps> = ({
  result,
  onArtistClick,
}) => {
  // Get the best thumbnail (prefer larger ones)
  const thumbnail = result.thumbnails?.[result.thumbnails.length - 1]?.url;

  const handleCardClick = () => {
    onArtistClick(result.browseId, result.name);
  };

  return (
    <Card
      className="overflow-hidden hover:shadow-md transition-shadow cursor-pointer py-4"
      onClick={handleCardClick}
    >
      <CardContent className="">
        <div className="flex items-center gap-3 sm:gap-4">
          {/* Circular Artist Avatar */}
          <div className="w-12 h-12 sm:w-16 sm:h-16 rounded-full overflow-hidden flex-shrink-0 bg-muted">
            {thumbnail ? (
              <img
                src={thumbnail}
                alt={result.name}
                className="w-full h-full object-cover"
                loading="lazy"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <User className="w-6 h-6 sm:w-8 sm:h-8 text-muted-foreground" />
              </div>
            )}
          </div>

          {/* Artist Info */}
          <div className="flex-1 min-w-0">
            <h3
              className="font-semibold text-foreground line-clamp-1 text-sm sm:text-base"
              title={result.name}
            >
              {result.name}
            </h3>
            {result.subscribers && (
              <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
                {result.subscribers}
              </p>
            )}
          </div>

          {/* View Button */}
          <div className="flex-shrink-0">
            <Button
              onClick={(e) => {
                e.stopPropagation();
                handleCardClick();
              }}
              variant="outline"
              size="sm"
              className="text-xs sm:text-sm"
            >
              View
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
