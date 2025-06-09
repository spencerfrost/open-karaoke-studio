import React, { useState } from "react";
import { Song } from "@/types/Song";
import { useSongs } from "@/hooks/useSongs";
import { Music, ImageIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface ArtworkDisplayProps {
  song: Song;
  size?: "small" | "medium" | "large";
  className?: string;
  showFallback?: boolean;
}

export const ArtworkDisplay: React.FC<ArtworkDisplayProps> = ({
  song,
  size = "medium",
  className = "",
  showFallback = true,
}) => {
  const { getArtworkUrl } = useSongs();
  const [imageError, setImageError] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const artworkUrl = getArtworkUrl(song, size);

  const sizeClasses = {
    small: "w-12 h-12",
    medium: "w-20 h-20",
    large: "w-48 h-48",
  };

  const iconSizes = {
    small: 16,
    medium: 24,
    large: 48,
  };

  const fallbackClasses = cn(
    "flex items-center justify-center bg-muted/20 border border-muted rounded-lg",
    sizeClasses[size],
    className
  );

  const imageClasses = cn(
    "object-cover rounded-lg",
    sizeClasses[size],
    className
  );

  // Handle image load
  const handleImageLoad = () => {
    setIsLoading(false);
  };

  // Handle image error
  const handleImageError = () => {
    setImageError(true);
    setIsLoading(false);
  };

  // Show fallback if no artwork URL, error, or showFallback is false
  if (!artworkUrl || imageError || !showFallback) {
    return (
      <div className={fallbackClasses} title="No artwork available">
        <Music size={iconSizes[size]} className="text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className={cn("relative", className)}>
      {isLoading && (
        <div className={cn(fallbackClasses, "absolute inset-0 z-10")}>
          <ImageIcon size={iconSizes[size]} className="text-muted-foreground animate-pulse" />
        </div>
      )}
      <img
        src={artworkUrl}
        alt={`${song.title} by ${song.artist} artwork`}
        className={imageClasses}
        onLoad={handleImageLoad}
        onError={handleImageError}
        loading="lazy"
      />
    </div>
  );
};
