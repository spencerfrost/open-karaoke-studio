import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";
import { YoutubeMusicSearchResult } from "@/types/Youtube";

interface YoutubeMusicResultCardProps {
  result: YoutubeMusicSearchResult;
  isLoading: boolean;
  onSelect: (result: YoutubeMusicSearchResult) => void;
  onArtistClick?: (artistId: string, artistName: string) => void;
}

export const YoutubeMusicResultCard: React.FC<YoutubeMusicResultCardProps> = ({
  result,
  isLoading,
  onSelect,
  onArtistClick,
}) => {
  // Get the best thumbnail (prefer larger ones)
  const thumbnail =
    result.thumbnails?.[result.thumbnails.length - 1]?.url || "";

  // Format duration if available
  const duration = result.duration || "";

  const handleSelect = () => {
    onSelect(result);
  };

  const handleArtistClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (result.artistId && onArtistClick) {
      onArtistClick(result.artistId, result.artist);
    }
  };

  const isArtistClickable = !!result.artistId && !!onArtistClick;

  return (
    <Card className="overflow-hidden hover:shadow-md transition-shadow py-2">
      <CardContent className="px-2 sm:px-4">
        {/* Mobile: Vertical Layout, Desktop: Horizontal Layout */}
        <div className="flex flex-col sm:flex-row gap-2 sm:gap-4">
          {/* Content */}
          <div className="flex-1 min-w-0 flex gap-4">
            {/* Thumbnail */}
            <div className="w-12 h-12 sm:w-16 sm:h-16 rounded overflow-hidden flex-shrink-0">
              <img
                src={thumbnail}
                alt={result.title}
                className="w-full h-full object-cover"
                loading="lazy"
              />
            </div>
            <div className="flex-1 min-w-0">
              <h3
                className="font-medium text-foreground line-clamp-2 mb-0.5 sm:mb-1 text-sm sm:text-base"
                title={result.title}
              >
                {result.title}
              </h3>
              <p className="text-xs sm:text-sm text-muted-foreground line-clamp-1">
                {isArtistClickable ? (
                  <button
                    onClick={handleArtistClick}
                    className="hover:text-primary hover:underline transition-colors text-left"
                    title={`Browse songs by ${result.artist}`}
                  >
                    {result.artist}
                  </button>
                ) : (
                  <span>{result.artist}</span>
                )}
                {result.album && (
                  <span className="text-muted-foreground">
                    {" "}
                    • {result.album}
                  </span>
                )}
              </p>
              {duration && (
                <p className="text-xs text-muted-foreground mt-0.5 sm:mt-1">
                  {duration}
                </p>
              )}
            </div>
          </div>

          {/* Action Button */}
          <div className="flex-shrink-0 flex items-center justify-center w-full sm:w-auto">
            <Button
              onClick={handleSelect}
              disabled={isLoading || result.existsInLibrary}
              variant="default"
              size="sm"
              className="w-full sm:w-auto"
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Adding...
                </>
              ) : result.existsInLibrary ? (
                "Already Added"
              ) : (
                "Add to Library"
              )}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
