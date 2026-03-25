import React from "react";
import { BaseResultCard } from "./shared/BaseResultCard";
import { YouTubeResultCardProps } from "./shared/types";
import { YouTubeAudioPreview } from "./shared/YouTubeAudioPreview";

// Helper function to format duration from seconds
const formatDuration = (seconds: number) => {
  if (!seconds) return "0:00";
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
};

export const YouTubeResultCard: React.FC<YouTubeResultCardProps> = ({
  result,
  isLoading,
  onSelect,
}) => {
  const handleSelect = () => {
    onSelect(result);
  };

  return (
    <BaseResultCard
      thumbnail={result.thumbnail}
      title={result.title}
      subtitle={result.channel}
      duration={formatDuration(result.duration)}
      isLoading={isLoading}
      onSelect={handleSelect}
    >
      <YouTubeAudioPreview videoId={result.id} />
    </BaseResultCard>
  );
};
