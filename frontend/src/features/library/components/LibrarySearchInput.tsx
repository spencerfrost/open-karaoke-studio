import React, { useEffect, useRef, useState } from "react";
import { Search, X, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

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
  className?: string;
}

const LibrarySearchInput: React.FC<LibrarySearchInputProps> = ({
  searchTerm,
  onSearchChange,
  isLoading,
  placeholder = "Search songs and artists...",
  debounceMs = 500,
  className = "",
}) => {
  const [inputValue, setInputValue] = useState(searchTerm);
  const debouncedValue = useDebouncedValue(inputValue, debounceMs);

  // Refs for values that should be read but not trigger the debounce effect
  const searchTermRef = useRef(searchTerm);
  searchTermRef.current = searchTerm;
  const onSearchChangeRef = useRef(onSearchChange);
  onSearchChangeRef.current = onSearchChange;

  // Keep local input in sync with external searchTerm
  useEffect(() => {
    setInputValue(searchTerm);
  }, [searchTerm]);

  // Emit debounced value
  useEffect(() => {
    if (debouncedValue !== searchTermRef.current) {
      onSearchChangeRef.current(debouncedValue);
    }
  }, [debouncedValue]);

  const handleClear = () => {
    setInputValue("");
    onSearchChange("");
  };

  return (
    <div className={`relative w-full ${className}`}>
      {/* Search Icon */}
      <Search
        size={20}
        className="absolute left-3 top-1/2 transform -translate-y-1/2 text-primary"
      />

      {/* Search Input */}
      <Input
        type="text"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        placeholder={placeholder}
        className="px-12 py-6 border-primary text-foreground bg-accent/20
                   placeholder:text-foreground-dim focus:ring-primary focus:border-primary"
      />

      {/* Right side icons */}
      <div className="absolute right-3 top-1/2 transform -translate-y-1/2 flex items-center gap-2">
        {/* Loading Spinner */}
        {isLoading && (
          <Loader2 size={16} className="text-primary animate-spin" />
        )}

        {/* Clear Button */}
        {inputValue && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClear}
            className="h-6 w-6 p-0 hover:bg-primary/20 text-primary hover:text-foreground"
          >
            <X size={14} />
          </Button>
        )}
      </div>
    </div>
  );
};

export default LibrarySearchInput;
