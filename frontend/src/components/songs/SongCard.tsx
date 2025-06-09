import React, { useState } from "react";
import { Music, Heart, Play, ListPlus, Pencil } from "lucide-react";
import { SongDetailsDialog } from "./song-details/SongDetailsDialog";
import { Song } from "@/types/Song";
import { formatTime } from "@/utils/formatters";
import vintageTheme from "@/utils/theme";
import { useSongs } from "@/hooks/useSongs";
import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";
import { Badge } from "../ui/badge";

interface SongCardProps {
  song: Song;
  onAddToQueue: (song: Song) => void;
  onToggleFavorite: (song: Song) => void;
  onSongUpdated?: (song: Song) => void;
  compact?: boolean; // For list view
}

const SongCard: React.FC<SongCardProps> = ({
  song,
  onAddToQueue,
  onToggleFavorite,
  compact = false,
}) => {
  // Local state for dialog
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const colors = vintageTheme.colors;
  const { getArtworkUrl } = useSongs();
  const navigate = useNavigate();

  // Get artwork URL with intelligent fallbacks
  const artworkUrl = getArtworkUrl(song, compact ? "small" : "medium");

  // Helper functions for dialog
  const handleCardClick = () => {
    setIsDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setIsDialogOpen(false);
  };

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
      <>
        <div
          className="rounded-lg p-3 flex items-center cursor-pointer hover:shadow-md transition-shadow"
          style={cardStyle}
          onClick={handleCardClick}
        >
          <div
            className="h-12 w-12 rounded-md flex items-center justify-center mr-3 relative"
            style={{ backgroundColor: `${colors.orangePeel}20` }}
          >
            {artworkUrl ? (
              <img
                src={artworkUrl}
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

            {/* Show album with enhanced metadata */}
            {song.album !== "Unknown Album" && (
              <p
                className="text-xs opacity-60"
                style={{ color: colors.darkCyan }}
              >
                {song.album}
              </p>
            )}

            {/* Show genre if no album or different from album */}
            {song.genre && song.album === "Unknown Album" && (
              <p
                className="text-xs opacity-60"
                style={{ color: colors.darkCyan }}
              >
                {song.genre}
              </p>
            )}
          </div>

          <div className="text-right">
            <div className="text-sm opacity-60">
              {formatTime(song.duration)}
            </div>
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
            {formatTime(song.duration)}
          </div>
        </div>

        {/* Song Details Dialog */}
        <SongDetailsDialog
          song={song}
          isOpen={isDialogOpen}
          onClose={handleCloseDialog}
        />
      </>
    );
  }

  // Grid view (default)
  return (
    <div
      className="rounded-lg overflow-hidden shadow-md relative"
      style={cardStyle}
    >
      <div
        className="flex items-center justify-center relative"
        style={{ backgroundColor: `${colors.orangePeel}20` }}
      >
        <div className="aspect-video w-full relative">
          {song.syncedLyrics && (
            <Badge className="absolute top-2 right-2 z-10 bg-accent">
              Synced
            </Badge>
          )}
          {artworkUrl ? (
            <img
              src={artworkUrl}
              alt={song.title}
              className="h-full w-full object-cover aspect-video"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <Music size={64} style={{ color: colors.darkCyan }} />
            </div>
          )}
        </div>

        <button
          className="absolute inset-0 flex items-center justify-center bg-transparent"
          onClick={handleCardClick}
          aria-label="View song details"
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

        <div className="flex justify-between items-start mt-1">
          <p className="text-sm opacity-75">{song.artist}</p>
          <p className="text-xs opacity-60 mt-1 text-accent">
            {formatTime(song.duration)}
          </p>
        </div>

        {/* Album and Genre metadata side-by-side */}
        <div className="flex justify-between gap-2 mt-1">
          {song.album ? (
            <p className="text-xs opacity-60 text-accent whitespace-nowrap overflow-hidden text-ellipsis">
              📀 {song.album}
            </p>
          ) : (
            <div className="text-xs opacity-0 text-accent whitespace-nowrap overflow-hidden text-ellipsis">
              {/* blank placeholder for flex alignment */}
            </div>
          )}
          {song.genre && (
            <p className="text-xs opacity-60 text-accent whitespace-nowrap overflow-hidden text-ellipsis">
              🎵 {song.genre}
            </p>
          )}
        </div>

        <div className="flex flex-wrap gap-1 mt-2">
          <Button
            variant="ghost"
            className="flex-1"
            onClick={() => {
              navigate(`/player/${song.id}`);
            }}
            aria-label="Play song"
          >
            <Play className="h-5 w-5" />
          </Button>
          {/* <Button
            variant="ghost"
            className="flex-1"
            onClick={() => onAddToQueue(song)}
            aria-label="Add to queue"
          >
            <ListPlus className="h-5 w-5" />
          </Button> */}
          <Button
            variant="ghost"
            className="flex-1 text-accent"
            onClick={handleCardClick}
            aria-label="View details"
          >
            <Pencil className="h-5 w-5" />
          </Button>
        </div>
      </div>

      {/* Song Details Dialog */}
      <SongDetailsDialog
        song={song}
        isOpen={isDialogOpen}
        onClose={handleCloseDialog}
      />
    </div>
  );
};

export default SongCard;
