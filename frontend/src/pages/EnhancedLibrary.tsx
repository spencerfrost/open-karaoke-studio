import React, { useState } from 'react';
import { Filter, Music } from 'lucide-react';
import AppLayout from '@/components/layout/AppLayout';
import SearchableInfiniteArtists from '../components/library/SearchableInfiniteArtists';
import { useSongs } from '@/hooks/useSongs';
import { Song } from '@/types/Song';
import { useNavigate } from 'react-router-dom';
import vintageTheme from '@/utils/theme';
import { Button } from '@/components/ui/button';

const EnhancedLibraryPage: React.FC = () => {
  const navigate = useNavigate();
  const colors = vintageTheme.colors;
  
  // State
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);

  // Hooks
  const { useToggleFavorite } = useSongs();
  const toggleFavorite = useToggleFavorite();

  // Handlers
  const handleSongSelect = (song: Song) => {
    navigate(`/player/${song.id}`);
  };

  const handleToggleFavorite = async (song: Song) => {
    try {
      await toggleFavorite.mutateAsync({
        id: song.id,
        favorite: !song.favorite,
      });
    } catch (error) {
      console.error('Failed to toggle favorite:', error);
    }
  };

  const handleAddToQueue = (song: Song) => {
    navigate('/queue', { state: { songId: song.id } });
  };

  return (
    <AppLayout>
      <div className="mb-6">
        <h1
          className="text-2xl font-semibold mb-6"
          style={{ color: colors.orangePeel }}
        >
          Song Library
        </h1>

        {/* Controls */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Music size={20} style={{ color: colors.orangePeel }} />
              <span style={{ color: colors.lemonChiffon }}>Browse by Artist</span>
            </div>
          </div>

          {/* Advanced Filters Button */}
          <Button
            variant="outline"
            onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
            style={{
              borderColor: colors.orangePeel,
              color: colors.orangePeel,
            }}
          >
            <Filter size={16} className="mr-2" />
            Advanced Filters
          </Button>
        </div>

        {/* Advanced Filters Panel */}
        {showAdvancedFilters && (
          <div
            className="mb-6 p-4 border rounded-lg"
            style={{ borderColor: colors.orangePeel }}
          >
            <div className="text-sm opacity-60 mb-2">
              Advanced filtering options coming soon...
            </div>
            {/* TODO: Add genre, year, source filters here */}
          </div>
        )}

        {/* Main Content - Infinite Scrolling Artist Library */}
        <SearchableInfiniteArtists
          onSongSelect={handleSongSelect}
          onToggleFavorite={handleToggleFavorite}
          onAddToQueue={handleAddToQueue}
        />
      </div>
    </AppLayout>
  );
};

export default EnhancedLibraryPage;
