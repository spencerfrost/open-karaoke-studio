import React, { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Music, Play, Heart, Plus, MoreVertical } from "lucide-react";
import { SongDetailsDialog } from "./song-details/SongDetailsDialog";
import { Song } from "@/types/Song";
import { formatTime } from "@/utils/formatters";
import { useSongs } from "@/hooks/useSongs";
import { Button } from "@/components/ui/button";
import vintageTheme from "@/utils/theme";

interface HorizontalSongCardProps {
  song: Song;
  onSongSelect?: (song: Song) => void;
  onToggleFavorite?: (song: Song) => void;
  onAddToQueue?: (song: Song) => void;
}

const HorizontalSongCard: React.FC<HorizontalSongCardProps> = ({
  song,
  onSongSelect,
  onToggleFavorite,
  onAddToQueue,
}) => {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const { getArtworkUrl } = useSongs();
  const colors = vintageTheme.colors;

  const artworkUrl = getArtworkUrl(song, "small");

  const handleCloseDialog = () => {
    setIsDialogOpen(false);
  };

  const handlePlayClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onSongSelect?.(song);
  };

  const handleFavoriteClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onToggleFavorite?.(song);
  };

  const handleQueueClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onAddToQueue?.(song);
  };

  const handleDetailsClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsDialogOpen(true);
  };

  return (
    <>
      <Card 
        className="overflow-hidden hover:shadow-md transition-all duration-200 cursor-pointer group"
        style={{ 
          borderColor: `${colors.orangePeel}40`,
          backgroundColor: `${colors.lemonChiffon}05`
        }}
        onClick={() => onSongSelect?.(song)}
      >
        <CardContent className="p-3">
          <div className="flex items-center gap-3">
            {/* Album Artwork */}
            <div 
              className="relative flex-shrink-0 rounded overflow-hidden"
              style={{ width: '60px', height: '60px' }}
            >
              {song.syncedLyrics && (
                <Badge 
                  className="absolute -top-1 -right-1 z-10 text-xs px-1 py-0" 
                  variant="accent"
                  style={{
                    backgroundColor: colors.orangePeel,
                    color: colors.darkCyan,
                    fontSize: '0.6rem'
                  }}
                >
                  ♪
                </Badge>
              )}
              
              {artworkUrl ? (
                <img
                  src={artworkUrl}
                  alt={song.title}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div 
                  className="w-full h-full flex items-center justify-center"
                  style={{ backgroundColor: `${colors.orangePeel}20` }}
                >
                  <Music size={24} style={{ color: colors.orangePeel }} />
                </div>
              )}
            </div>

            {/* Song Info */}
            <div className="flex-1 min-w-0">
              <div className="flex justify-between items-start mb-1">
                <h4 
                  className="font-medium truncate text-sm"
                  style={{ color: colors.lemonChiffon }}
                >
                  {song.title}
                </h4>
                <span 
                  className="text-xs ml-2 flex-shrink-0"
                  style={{ color: `${colors.lemonChiffon}80` }}
                >
                  {formatTime(song.duration)}
                </span>
              </div>
              
              <p 
                className="text-xs truncate mb-1"
                style={{ color: `${colors.lemonChiffon}90` }}
              >
                {song.artist}
              </p>
              
              {song.album && (
                <p 
                  className="text-xs truncate"
                  style={{ color: `${colors.lemonChiffon}60` }}
                >
                  {song.album}
                </p>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={handlePlayClick}
                style={{ 
                  color: colors.orangePeel,
                  backgroundColor: 'transparent'
                }}
              >
                <Play size={14} />
              </Button>
              
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={handleFavoriteClick}
                style={{ 
                  color: song.favorite ? colors.orangePeel : `${colors.lemonChiffon}60`,
                  backgroundColor: 'transparent'
                }}
              >
                <Heart 
                  size={14} 
                  fill={song.favorite ? colors.orangePeel : 'none'} 
                />
              </Button>
              
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={handleQueueClick}
                style={{ 
                  color: `${colors.lemonChiffon}80`,
                  backgroundColor: 'transparent'
                }}
              >
                <Plus size={14} />
              </Button>
              
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={handleDetailsClick}
                style={{ 
                  color: `${colors.lemonChiffon}60`,
                  backgroundColor: 'transparent'
                }}
              >
                <MoreVertical size={14} />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Song Details Dialog */}
      <SongDetailsDialog
        song={song}
        isOpen={isDialogOpen}
        onClose={handleCloseDialog}
      />
    </>
  );
};

export default HorizontalSongCard;
