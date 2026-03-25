import { useState, useEffect } from "react";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";

interface UseSearchRefinementParams {
  initialQuery: string;
  onQueryChange?: (query: string) => void;
  debounceMs?: number;
}

/**
 * Hook for managing search query refinement in dialogs
 * Provides local state management with debounced updates
 */
export const useSearchRefinement = ({
  initialQuery,
  onQueryChange,
  debounceMs = 800,
}: UseSearchRefinementParams) => {
  const [localQuery, setLocalQuery] = useState(initialQuery);
  const debouncedQuery = useDebouncedValue(localQuery, debounceMs);

  // Update parent when debounced value changes
  useEffect(() => {
    if (debouncedQuery !== initialQuery && onQueryChange) {
      onQueryChange(debouncedQuery);
    }
  }, [debouncedQuery, onQueryChange, initialQuery]);

  // Update local state when initial query changes (external update)
  useEffect(() => {
    setLocalQuery(initialQuery);
  }, [initialQuery]);

  return {
    query: localQuery,
    setQuery: setLocalQuery,
    debouncedQuery,
    isDirty: localQuery !== initialQuery,
  };
};
