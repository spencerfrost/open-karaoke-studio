import React, { useState } from "react";
import { DialogHeader, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Music, Search, Check } from "lucide-react";
import { Song } from "@/types/Song";
import { useMetadata } from "@/hooks/api/useMetadata";

interface MetadataSearchTabProps {
  song: Song;
  onSelectResult: (metadata: Partial<Song>) => void;
}

const MetadataSearchTab: React.FC<MetadataSearchTabProps> = ({
  song,
  onSelectResult,
}) => {
  const [searchQuery, setSearchQuery] = useState({
    title: song.title,
    artist: song.artist,
    album: song.album || "",
  });
  const [searchResults, setSearchResults] = useState<Partial<Song>[]>([]);
  const [noResults, setNoResults] = useState(false);

  const { useSearchMetadata } = useMetadata();
  const searchMetadata = useSearchMetadata();

  const handleSearch = async () => {
    setNoResults(false);

    try {
      const results = await searchMetadata.mutateAsync({
        title: searchQuery.title,
        artist: searchQuery.artist,
        album: searchQuery.album,
      });

      setSearchResults(results || []);
      setNoResults(results?.length === 0);
    } catch (error) {
      console.error("Metadata search failed:", error);
      setNoResults(true);
    }
  };

  const handleApplyResult = (result: Partial<Song>) => {
    onSelectResult(result);
  };

  return (
    <div className="pt-6 h-full flex flex-col">
      {/* Header */}
      <DialogHeader className="flex-grow">
        <DialogTitle className="text-lg font-semibold">
          Search Metadata
        </DialogTitle>
        <DialogDescription>
          Find the correct metadata for your song.
          <br />
          Enter the title and artist, and we will search for you.
        </DialogDescription>
      </DialogHeader>

      {/* Search Form */}
      <div className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label className="text-background" htmlFor="searchTitle">
              Title
            </Label>
            <Input
              id="searchTitle"
              value={searchQuery.title}
              onChange={(e) =>
                setSearchQuery((prev) => ({ ...prev, title: e.target.value }))
              }
              className="w-full"
            />
          </div>

          <div className="space-y-2">
            <Label className="text-background" htmlFor="searchArtist">
              Artist
            </Label>
            <Input
              id="searchArtist"
              value={searchQuery.artist}
              onChange={(e) =>
                setSearchQuery((prev) => ({ ...prev, artist: e.target.value }))
              }
              className="w-full"
            />
          </div>

          <div className="space-y-2">
            <Label className="text-background" htmlFor="searchAlbum">
              Album (optional)
            </Label>
            <Input
              id="searchAlbum"
              value={searchQuery.album}
              onChange={(e) =>
                setSearchQuery((prev) => ({ ...prev, album: e.target.value }))
              }
              className="w-full"
              placeholder="Enter album name..."
            />
          </div>
        </div>

        <div className="flex justify-end">
          <Button
            className="flex items-center gap-2 bg-dark-cyan text-lemon-chiffon"
            onClick={handleSearch}
            disabled={searchMetadata.isPending}
          >
            <Search size={18} />
            {searchMetadata.isPending ? "Searching..." : "Search Metadata"}
          </Button>
        </div>
      </div>

      {searchResults.length > 0 && (
        <div className="text-sm text-gray-500 italic">
          Select a result to apply its metadata to your song
        </div>
      )}

      {/* Search Results */}
      {searchResults.length > 0 && (
        <div className="space-y-3 max-h-60 overflow-y-auto pr-2">
          {searchResults.map((result, index) => (
            <div
              key={result.id ?? index}
              className="flex items-start gap-3 p-3 rounded-md cursor-pointer hover:bg-gray-100 bg-lemon-chiffon/80 border-l-[3px] border-orange-peel"
            >
              <div className="h-16 w-16 rounded-md flex-shrink-0 flex items-center justify-center overflow-hidden bg-orange-peel/20">
                {result.coverArt ? (
                  <img
                    src={result.coverArt}
                    alt={result.title}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <Music size={24} className="text-dark-cyan" />
                )}
              </div>

              <div className="flex-1 min-w-0">
                <h4 className="font-medium text-sm">{result.title}</h4>
                <p className="text-xs opacity-75">
                  {result.artist} {result.album && `• ${result.album}`}{" "}
                  {result.year && `(${result.year})`}
                </p>
                {result.genre && (
                  <p className="text-xs mt-1">
                    <span className="px-2 py-0.5 rounded-full text-xs bg-dark-cyan/30 text-dark-cyan">
                      {result.genre}
                    </span>
                  </p>
                )}
              </div>

              <Button
                size="sm"
                variant="ghost"
                className="flex items-center gap-1 text-dark-cyan"
                onClick={() => handleApplyResult(result)}
              >
                <Check size={16} />
                Apply
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* No Results State */}
      {noResults && (
        <div className="text-center py-6 opacity-70">
          <Music
            size={48}
            className="mx-auto mb-2 text-orange-peel"
          />
          <p>No matches found. Try adjusting your search terms.</p>
        </div>
      )}
    </div>
  );
};

export default MetadataSearchTab;
