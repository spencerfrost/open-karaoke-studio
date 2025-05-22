import React, { useState } from "react";
import { Music, Heart, Play } from "lucide-react";
import MetadataEditor from "./MetadataEditor";
import { Song } from "../../types/Song";
import { formatTime } from "../../utils/formatters";
import vintageTheme from "../../utils/theme";
import { useSongs } from "../../hooks/useSongs";
import { Button } from "../ui/button";

interface SongCardProps {
  song: Song;
  onPlay: (song: Song) => void;
  onAddToQueue: (song: Song) => void;
  onToggleFavorite: (song: Song) => void;
  onSongUpdated?: (song: Song) => void;
  compact?: boolean; // For list view
}

const SongCard: React.FC<SongCardProps> = ({
  song,
  onPlay,
  onAddToQueue,
  onToggleFavorite,
  onSongUpdated,
  compact = false,
}) => {
  // Local state for inline preview
  const [previewSrc, setPreviewSrc] = useState<string | null>(null);
  const colors = vintageTheme.colors;
  const { getAudioUrl } = useSongs();

  // Vintage card style
  const cardStyle = {
    backgroundColor: colors.lemonChiffon,
    color: colors.russet,
    boxShadow: `0 4px 6px rgba(0, 0, 0, 0.2), inset 0 0 0 1px ${colors.orangePeel}`,
    position: "relative" as const,
    overflow: "hidden" as const,
  };

  // Button style
  const primaryButtonStyle = {
    backgroundColor: colors.darkCyan,
    color: colors.lemonChiffon,
    border: `1px solid ${colors.lemonChiffon}`,
    transition: "all 0.2s ease",
  };

  // Render different layouts based on compact prop
  if (compact) {
    // List view (compact)
    return (
      <div className="rounded-lg p-3 flex items-center" style={cardStyle}>
        <div
          className="h-12 w-12 rounded-md flex items-center justify-center mr-3"
          style={{ backgroundColor: `${colors.orangePeel}20` }}
        >
          {song.coverArt || song.thumbnail ? (
            <img
              src={`/api/songs/${song.coverArt || song.thumbnail}`}
              alt={song.title}
              className="h-full w-full object-cover rounded-md"
            />
          ) : (
            <Music size={24} style={{ color: colors.darkCyan }} />
          )}
        </div>

        <div className="flex-1">
          <h3 className="font-medium">{song.title}</h3>
          <p className="text-sm opacity-75">{song.artist}</p>
        </div>

        <div className="text-right">
          <div className="text-sm opacity-60">{formatTime(song.duration)}</div>
          <div className="mt-1">
            {song.status === "processing" && (
              <span style={{ color: colors.rust }} className="text-xs">
                Processing...
              </span>
            )}
            {song.status === "queued" && (
              <span style={{ color: colors.orangePeel }} className="text-xs">
                Queued
              </span>
            )}
            {song.status === "processed" && (
              <button
                className="px-2 py-1 rounded text-xs"
                style={primaryButtonStyle}
                onClick={() => onAddToQueue(song)}
              >
                Sing
              </button>
            )}
          </div>
        </div>

        <div className="flex flex-col items-center ml-3">
          <Button
            variant="ghost"
            onClick={() => onToggleFavorite(song)}
            aria-label={
              song.favorite ? "Remove from favorites" : "Add to favorites"
            }
          >
            <Heart
              className={`h-8 w-8 text-primary ${song.favorite && "fill-current"}`}
            />
          </Button>
          <MetadataEditor
            icon
            song={song}
            onSongUpdated={
              onSongUpdated ||
              ((updatedSong) => console.log("Song updated:", updatedSong))
            }
          />
        </div>
      </div>
    );
  }

  // Grid view (default)
  return (
    <div className="rounded-lg overflow-hidden shadow-md" style={cardStyle}>
      <div
        className="flex items-center justify-center relative"
        style={{ backgroundColor: `${colors.orangePeel}20` }}
      >
        <div className="aspect-video w-full">
          {song.coverArt || song.thumbnail ? (
            <img
              src={`/api/songs/${song.coverArt || song.thumbnail}`}
              alt={song.title}
              className="h-full w-full object-cover"
            />
          ) : (
            <Music size={64} style={{ color: colors.darkCyan }} />
          )}
        </div>

        <button
          className="absolute inset-0 flex items-center justify-center bg-transparent"
          onClick={() => {
            const url = getAudioUrl(song.id, "vocals");
            setPreviewSrc(url);
            onPlay(song);
          }}
          aria-label="Play song"
        >
          <div
            className="h-12 w-12 rounded-full items-center justify-center hidden hover:flex"
            style={{ backgroundColor: colors.darkCyan }}
          >
            <Play
              size={24}
              className="text-white"
              style={{ marginLeft: "2px" }}
            />
          </div>
        </button>
      </div>

      <div className="p-3">
        <div className="flex justify-between items-start">
          <h3 className="font-medium truncate">{song.title}</h3>
          <button
            onClick={() => onToggleFavorite(song)}
            aria-label={
              song.favorite ? "Remove from favorites" : "Add to favorites"
            }
          >
            <Heart
              className={`h-6 w-6 text-primary ${song.favorite && "fill-current"}`}
            />
          </button>
        </div>

        <p className="text-sm opacity-75">{song.artist}</p>

        <div className="flex justify-between items-center mt-2 text-xs">
          <MetadataEditor
            song={song}
            onSongUpdated={
              onSongUpdated ||
              ((updatedSong) => console.log("Song updated:", updatedSong))
            }
          />
          <span className="opacity-60">{formatTime(song.duration)}</span>
        </div>
      </div>
      {/* Inline audio player for preview */}
      {previewSrc && (
        <div className="p-3 bg-black bg-opacity-20">
          <audio controls src={previewSrc} autoPlay className="w-full" />
        </div>
      )}
    </div>
  );
};

export default SongCard;
