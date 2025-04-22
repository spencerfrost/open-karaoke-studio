import React, { useEffect, useState } from 'react';
import { Music, Search } from 'lucide-react';
import { useSongs } from '../context/SongsContext';
import SongCard from '../components/songs/SongCard';
import AppLayout from '../components/layout/AppLayout';
import { getSongs, toggleFavorite } from '../services/songService';
import { useNavigate } from 'react-router-dom';
import vintageTheme from '../utils/theme';

const LibraryPage: React.FC = () => {
  const { state, dispatch } = useSongs();
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const colors = vintageTheme.colors;

  // Fetch songs on component mount
  useEffect(() => {
    const fetchSongs = async () => {
      setIsLoading(true);
      const response = await getSongs();
      setIsLoading(false);
      
      if (response.data) {
        dispatch({ type: 'SET_SONGS', payload: response.data });
      }
    };
    
    fetchSongs();
  }, [dispatch]);

  // Handle search input
  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    dispatch({ type: 'SET_FILTER_TERM', payload: e.target.value });
  };

  // Handle filter status change
  const handleStatusFilter = (e: React.ChangeEvent<HTMLSelectElement>) => {
    dispatch({ 
      type: 'SET_FILTER_STATUS', 
      payload: e.target.value as any 
    });
  };

  // Handle favorites toggle
  const handleFavoritesFilter = (e: React.ChangeEvent<HTMLInputElement>) => {
    dispatch({ 
      type: 'SET_FILTER_FAVORITES', 
      payload: e.target.checked 
    });
  };

  // Handle song favorite toggle
  const handleToggleFavorite = async (song: any) => {
    const newFavoriteStatus = !song.favorite;
    
    // Optimistic update
    dispatch({
      type: 'UPDATE_SONG',
      payload: {
        id: song.id,
        updates: { favorite: newFavoriteStatus }
      }
    });
    
    // API call
    const response = await toggleFavorite(song.id, newFavoriteStatus);
    
    if (response.error) {
      // Revert on error
      dispatch({
        type: 'UPDATE_SONG',
        payload: {
          id: song.id,
          updates: { favorite: song.favorite }
        }
      });
    }
  };

  // Handle play song
  const handlePlaySong = (song: any) => {
    navigate(`/player/${song.id}`);
  };

  // Handle add to queue
  const handleAddToQueue = (song: any) => {
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
        
        {/* Search and filters */}
        <div className="mb-4">
          <div className="flex items-center border rounded-lg mb-4 relative overflow-hidden"
            style={{
              backgroundColor: `${colors.lemonChiffon}20`,
              borderColor: colors.orangePeel
            }}
          >
            <Search 
              size={20} 
              className="absolute left-3" 
              style={{ color: colors.orangePeel }}
            />
            <input
              type="text"
              placeholder="Search songs..."
              className="py-2 px-10 w-full bg-transparent focus:outline-none"
              style={{ color: colors.lemonChiffon }}
              value={state.filterTerm}
              onChange={handleSearch}
            />
          </div>
          
          <div className="flex flex-wrap gap-3">
            <select
              className="py-1 px-3 rounded border"
              style={{
                backgroundColor: `${colors.lemonChiffon}20`,
                borderColor: colors.orangePeel,
                color: colors.lemonChiffon
              }}
              value={state.filterStatus}
              onChange={handleStatusFilter}
            >
              <option value="all">All Statuses</option>
              <option value="processed">Processed</option>
              <option value="processing">Processing</option>
              <option value="queued">Queued</option>
            </select>
            
            <div className="flex items-center">
              <input
                type="checkbox"
                id="favorites"
                className="mr-2"
                checked={state.filterFavorites}
                onChange={handleFavoritesFilter}
              />
              <label 
                htmlFor="favorites"
                style={{ color: colors.lemonChiffon }}
              >
                Favorites Only
              </label>
            </div>
            
            <div className="flex ml-auto gap-2">
              <button 
                className={`px-3 py-1 rounded ${viewMode === 'grid' ? 'opacity-100' : 'opacity-60'}`}
                onClick={() => setViewMode('grid')}
                style={{
                  backgroundColor: viewMode === 'grid' ? colors.darkCyan : 'transparent'
                }}
              >
                Grid
              </button>
              <button 
                className={`px-3 py-1 rounded ${viewMode === 'list' ? 'opacity-100' : 'opacity-60'}`}
                onClick={() => setViewMode('list')}
                style={{
                  backgroundColor: viewMode === 'list' ? colors.darkCyan : 'transparent'
                }}
              >
                List
              </button>
            </div>
          </div>
        </div>
        
        {/* Loading state */}
        {isLoading && (
          <div 
            className="text-center py-8"
            style={{ color: colors.lemonChiffon }}
          >
            Loading songs...
          </div>
        )}
        
        {/* Empty state */}
        {!isLoading && state.filteredSongs.length === 0 && (
          <div 
            className="text-center py-12 rounded-lg"
            style={{ 
              backgroundColor: `${colors.lemonChiffon}10`,
              color: colors.lemonChiffon
            }}
          >
            <Music 
              size={48} 
              className="mx-auto mb-4" 
              style={{ color: colors.orangePeel }}
            />
            <h3 className="text-xl font-semibold mb-2">No songs found</h3>
            <p className="opacity-80">
              {state.filterTerm || state.filterStatus !== 'all' || state.filterFavorites
                ? 'Try adjusting your filters'
                : 'Add some songs to get started'}
            </p>
          </div>
        )}
        
        {/* Songs grid/list */}
        {!isLoading && state.filteredSongs.length > 0 && (
          viewMode === 'grid' ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {state.filteredSongs.map((song) => (
                <SongCard
                  key={song.id}
                  song={song}
                  onPlay={handlePlaySong}
                  onAddToQueue={handleAddToQueue}
                  onToggleFavorite={handleToggleFavorite}
                />
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              {state.filteredSongs.map((song) => (
                <SongCard
                  key={song.id}
                  song={song}
                  onPlay={handlePlaySong}
                  onAddToQueue={handleAddToQueue}
                  onToggleFavorite={handleToggleFavorite}
                  compact
                />
              ))}
            </div>
          )
        )}
      </div>
    </AppLayout>
  );
};

export default LibraryPage;
