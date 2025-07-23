import React, { useEffect, useState } from 'react';
import { Search, X, Loader2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

function useDebouncedValue<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const handler = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(handler);
  }, [value, delay]);
  return debounced;
}

interface LibrarySearchInputProps {
  searchTerm: string;
  onSearchChange: (term: string) => void;
  isLoading: boolean;
  placeholder?: string;
  debounceMs?: number;
}

const LibrarySearchInput: React.FC<LibrarySearchInputProps> = ({
  searchTerm,
  onSearchChange,
  isLoading,
  placeholder = "Search songs and artists...",
  debounceMs = 300,
}) => {
  const [inputValue, setInputValue] = useState(searchTerm);
  const debouncedValue = useDebouncedValue(inputValue, debounceMs);

  // Keep local input in sync with external searchTerm
  useEffect(() => {
    setInputValue(searchTerm);
  }, [searchTerm]);

  // Emit debounced value
  useEffect(() => {
    if (debouncedValue !== searchTerm) {
      onSearchChange(debouncedValue);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedValue]);

  const handleClear = () => {
    setInputValue('');
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
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
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
        {inputValue && (
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
