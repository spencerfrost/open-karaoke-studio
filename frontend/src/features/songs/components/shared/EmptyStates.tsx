import React from "react";
import { Search, Music, Video, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

interface EmptySearchStateProps {
  message?: string;
  description?: string;
}

export const EmptySearchState: React.FC<EmptySearchStateProps> = ({
  message = "Start searching",
  description = "Enter a song name, artist, or any search term to find music.",
}) => {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <Search className="h-12 w-12 text-muted-foreground mb-4" />
      <h3 className="text-lg font-medium text-foreground mb-2">{message}</h3>
      <p className="text-muted-foreground text-center">{description}</p>
    </div>
  );
};

interface NoResultsStateProps {
  query: string;
  source: "youtube-music" | "youtube";
  onRetry?: () => void;
}

export const NoResultsState: React.FC<NoResultsStateProps> = ({
  query,
  source,
  onRetry,
}) => {
  const sourceLabel = source === "youtube-music" ? "YouTube Music" : "YouTube";
  const Icon = source === "youtube-music" ? Music : Video;

  return (
    <div className="flex flex-col items-center justify-center py-12">
      <Icon className="h-12 w-12 text-muted-foreground mb-4" />
      <h3 className="text-lg font-medium text-foreground mb-2">
        No results found
      </h3>
      <p className="text-muted-foreground text-center mb-4">
        No songs found on {sourceLabel} for "{query}".
      </p>
      <div className="text-sm text-muted-foreground text-center space-y-1">
        <p>Try:</p>
        <ul className="list-disc list-inside space-y-1">
          <li>Different search terms or spelling</li>
          <li>Searching on the other tab</li>
          <li>Using just the artist or song name</li>
        </ul>
      </div>
      {onRetry && (
        <Button variant="outline" onClick={onRetry} className="mt-4">
          Try Again
        </Button>
      )}
    </div>
  );
};

interface SearchErrorStateProps {
  error: Error;
  onRetry?: () => void;
}

export const SearchErrorState: React.FC<SearchErrorStateProps> = ({
  error,
  onRetry,
}) => {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <AlertCircle className="h-12 w-12 text-destructive mb-4" />
      <h3 className="text-lg font-medium text-foreground mb-2">
        Search failed
      </h3>
      <p className="text-muted-foreground text-center mb-4">
        {error.message || "Something went wrong while searching."}
      </p>
      {onRetry && (
        <Button variant="outline" onClick={onRetry}>
          Try Again
        </Button>
      )}
    </div>
  );
};
