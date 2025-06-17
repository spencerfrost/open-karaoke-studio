import React from 'react';
import { Search, X, Loader2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

interface LibrarySearchInputProps {
  searchTerm: string;
  onSearchChange: (term: string) => void;
  isLoading: boolean;
  placeholder?: string;
}

const LibrarySearchInput: React.FC<LibrarySearchInputProps> = ({
  searchTerm,
  onSearchChange,
  isLoading,
  placeholder = "Search songs and artists..."
}) => {
  const handleClear = () => {
    onSearchChange('');
  };

  return (
    <div className="relative">
      {/* Search Icon */}
      <Search
        size={20}
        className="absolute left-3 top-1/2 transform -translate-y-1/2 text-orange-peel"
      />

      {/* Search Input */}
      <Input
        type="text"
        value={searchTerm}
        onChange={(e) => onSearchChange(e.target.value)}
        placeholder={placeholder}
        className="pl-10 pr-20 border-orange-peel text-lemon-chiffon bg-dark-cyan/20
                   placeholder:text-lemon-chiffon/60 focus:ring-orange-peel focus:border-orange-peel"
      />

      {/* Right side icons */}
      <div className="absolute right-3 top-1/2 transform -translate-y-1/2 flex items-center gap-2">
        {/* Loading Spinner */}
        {isLoading && (
          <Loader2 size={16} className="text-orange-peel animate-spin" />
        )}

        {/* Clear Button */}
        {searchTerm && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClear}
            className="h-6 w-6 p-0 hover:bg-orange-peel/20 text-orange-peel hover:text-lemon-chiffon"
          >
            <X size={14} />
          </Button>
        )}
      </div>
    </div>
  );
};

export default LibrarySearchInput;
