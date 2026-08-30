/**
 * QueueEnded - Content displayed when a song finishes playing and queue is empty
 *
 * Shows song suggestions (like YouTube's end screen).
 * Replaces the lyrics display when the song ends and no more songs are in queue.
 */

import React from "react";
import { Music, Play, Library } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  useSongSuggestions,
  getSuggestionReasonText,
} from "../../hooks/useSongSuggestions";
import { useSongs } from "@/hooks/api/useSongs";
import { useOpenSongSelect } from "@/hooks/useOpenSongSelect";
import { useAddToKaraokeQueue } from "@/hooks/api/useKaraokeQueue";
import { useRoster } from "@/hooks/api/useRoster";
import { useSessionStore } from "@/stores/sessionStore";
import { toast } from "sonner";
import type { Song } from "@/types/Song";

interface QueueEndedProps {
  /** The song that just finished */
  currentSong: Song;
  /** Callback when a suggested song is selected */
  onSelectSong?: (song: Song) => void;
  /** Optional class name */
  className?: string;
}

interface SuggestionCardProps {
  song: Song;
  artworkUrl: string | null;
  onClick: () => void;
}

const SuggestionCard: React.FC<SuggestionCardProps> = ({
  song,
  artworkUrl,
  onClick,
}) => {
  return (
    <button
      onClick={onClick}
      className="group relative bg-overlay/60 hover:bg-overlay/80 rounded-lg overflow-hidden transition-all duration-200 hover:scale-105 hover:ring-2 hover:ring-orange-peel/50 text-left"
    >
      {/* Artwork */}
      <div className="aspect-video w-full relative">
        {artworkUrl ? (
          <img
            src={artworkUrl}
            alt={song.title}
            className="object-cover w-full h-full"
          />
        ) : (
          <div className="flex items-center justify-center w-full h-full bg-primary/20">
            <Music size={32} className="text-cyan-700" />
          </div>
        )}

        {/* Play overlay on hover */}
        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-overlay/40">
          <div className="bg-orange-peel/90 rounded-full p-2">
            <Play className="w-6 h-6 text-card-foreground fill-card-foreground" />
          </div>
        </div>
      </div>

      {/* Song info */}
      <div className="p-2">
        <h4 className="text-sm font-medium text-foreground truncate">
          {song.title}
        </h4>
        <p className="text-xs text-foreground/60 truncate">{song.artist}</p>
      </div>
    </button>
  );
};

export const QueueEnded: React.FC<QueueEndedProps> = ({
  currentSong,
  onSelectSong,
  className = "",
}) => {
  const openSongSelect = useOpenSongSelect();
  const { getArtworkUrl } = useSongs();
  const { displayCode } = useSessionStore();
  const addToQueue = useAddToKaraokeQueue(displayCode || undefined);
  const { data: roster } = useRoster(displayCode || undefined);
  // The most recently joined active performer is the closest proxy the roster
  // gives us to "who's most likely up next" - falls back to "Host" only when
  // the roster is empty.
  const defaultSinger = roster?.length
    ? roster[roster.length - 1].name
    : "Host";

  const { suggestions, isLoading } = useSongSuggestions({
    currentSong,
    limit: 4, // Show up to 4 suggestions
  });

  const handleSongSelect = (song: Song) => {
    if (onSelectSong) {
      onSelectSong(song);
      return;
    }
    addToQueue.mutate(
      { songId: song.id, singer: defaultSinger },
      {
        onSuccess: () => toast.success(`Added "${song.title}" to the queue`),
        onError: () =>
          toast.error(`Failed to add "${song.title}" to the queue`),
      },
    );
  };

  const hasSuggestions = suggestions.length > 0;
  const suggestionReason = hasSuggestions
    ? getSuggestionReasonText(suggestions[0].reason)
    : null;

  return (
    <div
      className={`flex items-center justify-center w-full h-full ${className}`}
    >
      <div className="flex flex-col items-center gap-6 p-6 max-w-4xl w-full">
        {/* Header */}
        <div className="text-center">
          <h2 className="text-2xl font-bold text-foreground mb-1">
            Queue Complete! 🎉
          </h2>
          <p className="text-foreground/60">No more songs left to sing</p>
        </div>

        {/* Suggestions Section */}
        {hasSuggestions && (
          <div className="w-full">
            <h3 className="text-sm font-medium text-foreground/80 mb-3">
              {suggestionReason}
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {suggestions.map((suggestion) => (
                <SuggestionCard
                  key={suggestion.song.id}
                  song={suggestion.song}
                  artworkUrl={getArtworkUrl(suggestion.song, "medium")}
                  onClick={() => handleSongSelect(suggestion.song)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Loading state for suggestions */}
        {isLoading && (
          <div className="text-foreground/60 text-sm">
            Finding more songs...
          </div>
        )}

        {/* No suggestions fallback */}
        {!isLoading && !hasSuggestions && (
          <div className="text-foreground/60 text-sm text-center">
            <p>No other songs by {currentSong.artist} in your library.</p>
            <p className="mt-1">
              Add more songs to continue your karaoke session!
            </p>
          </div>
        )}

        {/* Browse Library Button */}
        <div className="flex items-center gap-4 mt-4">
          <Button
            variant="outline"
            size="lg"
            onClick={() => openSongSelect()}
            className="bg-overlay/50 hover:bg-overlay/70 border-glass-border/30 hover:border-glass-border/50 text-foreground gap-2"
          >
            <Library className="w-5 h-5" />
            Browse Library
          </Button>
        </div>
      </div>
    </div>
  );
};

export default QueueEnded;
