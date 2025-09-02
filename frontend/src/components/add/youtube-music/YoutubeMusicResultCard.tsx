import React from "react";
import { BaseResultCard } from "../shared/BaseResultCard";
import { YoutubeMusicSearchResult } from "@/types/YoutubeMusic";

interface YoutubeMusicResultCardProps {
  result: YoutubeMusicSearchResult;
  isLoading: boolean;
  onSelect: (result: YoutubeMusicSearchResult) => void;
}

export const YoutubeMusicResultCard: React.FC<YoutubeMusicResultCardProps> = ({
  result,
  isLoading,
  onSelect,
}) => {
  // Get the best thumbnail (prefer larger ones)
  const thumbnail =
    result.thumbnails?.[result.thumbnails.length - 1]?.url || "";

  // Format duration if available
  const duration = result.duration || "";

  // Build subtitle with album info if available
  const subtitle = result.album
    ? `${result.artist} • ${result.album}`
    : result.artist;

  const handleSelect = () => {
    onSelect(result);
  };

  return (
    <BaseResultCard
      thumbnail={thumbnail}
      title={result.title}
      subtitle={subtitle}
      duration={duration}
      isLoading={isLoading}
      onSelect={handleSelect}
    >
      {/* Additional YouTube Music specific metadata could go here */}
    </BaseResultCard>
  );
};
