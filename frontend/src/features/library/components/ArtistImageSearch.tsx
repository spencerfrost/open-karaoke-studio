import React, { useState } from "react";
import { Loader2, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useApiQuery } from "@/hooks/api/useApi";
import { createLogger } from "@/lib/logger";

const logger = createLogger("component:ArtistImageSearch");

interface ImageCandidate {
  thumb: string;
  uri: string;
  title: string;
}

interface ImageSearchResponse {
  results: ImageCandidate[];
}

interface ArtistImageSearchProps {
  artistId: number;
  initialQuery: string;
  onSelect: (imageUrl: string) => void;
  isApplying: boolean;
}

const ArtistImageSearch: React.FC<ArtistImageSearchProps> = ({
  artistId,
  initialQuery,
  onSelect,
  isApplying,
}) => {
  const [inputValue, setInputValue] = useState(initialQuery);
  const [activeQuery, setActiveQuery] = useState(initialQuery);

  const { data, isLoading, error } = useApiQuery<ImageSearchResponse>(
    ["artist-image-search", artistId, activeQuery],
    `artists/${artistId}/images/search?q=${encodeURIComponent(activeQuery)}`,
    {
      enabled: !!activeQuery,
      staleTime: 5 * 60 * 1000,
      retry: false,
    },
  );

  const handleSearch = () => {
    const trimmed = inputValue.trim();
    if (trimmed) {
      logger.debug("Searching artist images", { query: trimmed });
      setActiveQuery(trimmed);
    }
  };

  const isBusy = isLoading || isApplying;

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <Input
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="Search Discogs…"
          disabled={isBusy}
          autoFocus
        />
        <Button
          variant="outline"
          size="icon"
          onClick={handleSearch}
          disabled={isBusy || !inputValue.trim()}
          aria-label="Search"
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Search className="h-4 w-4" />
          )}
        </Button>
      </div>

      {error && (
        <p className="text-sm text-destructive">
          Search failed: {(error as Error).message}
        </p>
      )}

      {isApplying && (
        <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Downloading image…
        </div>
      )}

      {!isApplying && data && data.results.length === 0 && (
        <p className="text-sm text-muted-foreground text-center py-6">
          No images found.
        </p>
      )}

      {!isApplying && data && data.results.length > 0 && (
        <div className="grid grid-cols-4 gap-2 max-h-[280px] overflow-y-auto pr-1">
          {data.results.map((candidate, i) => (
            <button
              key={i}
              type="button"
              className="relative group aspect-square overflow-hidden rounded-md border border-border hover:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={() => onSelect(candidate.uri)}
              disabled={isBusy}
              title={candidate.title}
            >
              <img
                src={candidate.thumb}
                alt={candidate.title}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                onError={(e) => {
                  e.currentTarget.style.display = "none";
                }}
              />
              {candidate.title && (
                <div className="absolute inset-x-0 bottom-0 bg-black/60 text-white text-[10px] px-1 py-0.5 truncate opacity-0 group-hover:opacity-100 transition-opacity">
                  {candidate.title}
                </div>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default ArtistImageSearch;
