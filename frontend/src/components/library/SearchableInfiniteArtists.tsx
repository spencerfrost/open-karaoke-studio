import React, { useState } from 'react';
import { Search } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { useDebouncedValue } from '@/hooks/useDebouncedValue';
import InfiniteArtistAccordion from './InfiniteArtistAccordion';
import { Song } from '@/types/Song';

interface SearchableInfiniteArtistsProps {
  onSongSelect?: (song: Song) => void;
  onToggleFavorite?: (song: Song) => void;
  onAddToQueue?: (song: Song) => void;
  className?: string;
}

const SearchableInfiniteArtists: React.FC<SearchableInfiniteArtistsProps> = ({
  onSongSelect,
  onToggleFavorite,
  onAddToQueue,
  className = '',
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const debouncedSearch = useDebouncedValue(searchTerm, 300);

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Search Input */}
      <div className="relative">
        <Search
          size={20}
          className="absolute left-3 top-1/2 transform -translate-y-1/2 opacity-60 text-orange-peel"
        />
        <Input
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Search artists..."
          className="pl-10 border-orange-peel text-lemon-chiffon bg-dark-cyan/20"
        />
      </div>

      {/* Infinite Artist Accordion */}
      <InfiniteArtistAccordion
        searchTerm={debouncedSearch}
        onSongSelect={onSongSelect}
        onToggleFavorite={onToggleFavorite}
        onAddToQueue={onAddToQueue}
      />
    </div>
  );
};

export default SearchableInfiniteArtists;
