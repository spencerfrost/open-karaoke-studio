import React, { useState } from 'react';
import { Filter, Music } from 'lucide-react';
import AppLayout from '@/components/layout/AppLayout';
import SearchableInfiniteArtists from '../components/library/SearchableInfiniteArtists';
import { useSongs } from '@/hooks/useSongs';
import { Song } from '@/types/Song';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';

const LibraryPage: React.FC = () => {
  const navigate = useNavigate();
  
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
        <h1 className="text-2xl font-semibold mb-6 text-orange-peel">
          Song Library
        </h1>

        {/* Controls */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Music size={20} className="text-orange-peel" />
              <span className="text-lemon-chiffon">Browse by Artist</span>
            </div>
          </div>

          {/* Advanced Filters Button */}
          <Button
            variant="outline"
            onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
            className="border-orange-peel text-orange-peel"
          >
            <Filter size={16} className="mr-2" />
            Advanced Filters
          </Button>
        </div>

        {/* Advanced Filters Panel */}
        {showAdvancedFilters && (
          <div className="mb-6 p-4 border border-orange-peel rounded-lg">
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

export default LibraryPage;
