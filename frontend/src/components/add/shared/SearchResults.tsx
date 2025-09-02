import React from "react";
import { SearchLoadingState } from "./LoadingStates";
import { EmptySearchState, SearchErrorState } from "./EmptyStates";

// Generic search results component that can display any type of result with any result card
interface SearchResultsProps<TResult> {
  results: TResult[];
  isLoading: boolean;
  error: Error | null;
  onSelect: (result: TResult) => void;
  loadingStates: Record<string, boolean>;
  resultCardComponent: React.ComponentType<{
    result: TResult;
    isLoading: boolean;
    onSelect: () => void;
  }>;
  keyExtractor: (result: TResult) => string;
  emptyMessage: string;
  emptyDescription: string;
}

export const SearchResults = <TResult,>({
  results,
  isLoading,
  error,
  onSelect,
  loadingStates,
  resultCardComponent: ResultCard,
  keyExtractor,
  emptyMessage,
  emptyDescription,
}: SearchResultsProps<TResult>) => {
  // Show loading state
  if (isLoading) {
    return <SearchLoadingState />;
  }

  // Show error state
  if (error) {
    return <SearchErrorState error={error} />;
  }

  // Show empty state when no query has been made
  if (results.length === 0) {
    return (
      <EmptySearchState
        message={emptyMessage}
        description={emptyDescription}
      />
    );
  }

  // Show results
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4">
        {results.map((result) => {
          const key = keyExtractor(result);
          return (
            <ResultCard
              key={key}
              result={result}
              isLoading={loadingStates[key] || false}
              onSelect={() => onSelect(result)}
            />
          );
        })}
      </div>
    </div>
  );
};