import React from "react";
import { Song } from "@/types/Song";
import { Badge } from "@/components/ui/badge";
import { Music, Globe } from "lucide-react";
import { cn } from "@/lib/utils";

interface SourceBadgesProps {
  song: Song;
  size?: "small" | "medium";
  className?: string;
  showIcons?: boolean;
}

export const SourceBadges: React.FC<SourceBadgesProps> = ({
  song,
  size = "medium",
  className = "",
  showIcons = true,
}) => {
  const badgeSize = size === "small" ? "text-xs px-1 py-0" : "text-xs px-2 py-1";
  const iconSize = size === "small" ? 10 : 12;

  const badges = [];

  // iTunes badge
  if (song.itunesTrackId) {
    badges.push(
      <Badge
        key="itunes"
        variant="secondary"
        className={cn(badgeSize, "bg-blue-100 text-blue-800 border-blue-200", className)}
      >
        {showIcons && <Music size={iconSize} className="mr-1" />}
        iTunes
      </Badge>
    );
  }

  // YouTube badge
  if (song.videoId) {
    badges.push(
      <Badge
        key="youtube"
        variant="secondary"
        className={cn(badgeSize, "bg-red-100 text-red-800 border-red-200", className)}
      >
        {showIcons && <Globe size={iconSize} className="mr-1" />}
        YouTube
      </Badge>
    );
  }

  // High quality metadata badge
  if (song.itunesTrackId && song.videoId) {
    badges.push(
      <Badge
        key="complete"
        variant="secondary"
        className={cn(badgeSize, "bg-green-100 text-green-800 border-green-200", className)}
      >
        Complete
      </Badge>
    );
  }

  // Lyrics badge
  if (song.syncedLyrics) {
    badges.push(
      <Badge
        key="synced-lyrics"
        variant="secondary"
        className={cn(badgeSize, "bg-purple-100 text-purple-800 border-purple-200", className)}
      >
        Synced Lyrics
      </Badge>
    );
  } else if (song.lyrics) {
    badges.push(
      <Badge
        key="lyrics"
        variant="outline"
        className={cn(badgeSize, "border-purple-200 text-purple-700", className)}
      >
        Lyrics
      </Badge>
    );
  }

  if (badges.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap gap-1">
      {badges}
    </div>
  );
};
