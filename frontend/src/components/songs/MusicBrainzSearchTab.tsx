import React, { useState } from "react";
import { DialogHeader, DialogDescription, DialogTitle } from "../ui/dialog";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Music, Search, Check } from "lucide-react";
import { Song } from "../../types/Song";
import vintageTheme from "../../utils/theme";
import { searchMusicBrainz } from "../../services/songService";

interface MusicBrainzSearchTabProps {
  song: Song;
  onSelectResult: (metadata: Partial<Song>) => void;
}

const MusicBrainzSearchTab: React.FC<MusicBrainzSearchTabProps> = ({
  song,
  onSelectResult,
}) => {
  const colors = vintageTheme.colors;
  const [isSearching, setIsSearching] = useState(false);
  const [searchQuery, setSearchQuery] = useState({
    title: song.title,
    artist: song.artist,
  });
  const [searchResults, setSearchResults] = useState<Partial<Song>[]>([]);
  const [noResults, setNoResults] = useState(false);

  const handleSearch = async () => {
    setIsSearching(true);
    setNoResults(false);

    try {
      const response = await searchMusicBrainz({
        title: searchQuery.title,
        artist: searchQuery.artist,
      });

      setSearchResults(response.data || []);
      setNoResults(response.data?.length === 0);
    } catch (error) {
      console.error("MusicBrainz search failed:", error);
      setNoResults(true);
    } finally {
      setIsSearching(false);
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
          Search MusicBrainz
        </DialogTitle>
        <DialogDescription>
          Find the correct metadata for your song.
          <br />
          Enter the title and artist, and we will search MusicBrainz for you.
        </DialogDescription>
      </DialogHeader>

      {/* Search Form */}
      <div className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
        </div>

        <div className="flex justify-end">
          <Button
            className="flex items-center gap-2"
            onClick={handleSearch}
            disabled={isSearching}
            style={{
              backgroundColor: colors.darkCyan,
              color: colors.lemonChiffon,
            }}
          >
            <Search size={18} />
            {isSearching ? "Searching..." : "Search MusicBrainz"}
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
              key={result.musicbrainzId ?? index}
              className="flex items-start gap-3 p-3 rounded-md cursor-pointer hover:bg-gray-100"
              style={{
                backgroundColor: `${colors.lemonChiffon}80`,
                borderLeft: `3px solid ${colors.orangePeel}`,
              }}
            >
              <div
                className="h-16 w-16 rounded-md flex-shrink-0 flex items-center justify-center overflow-hidden"
                style={{ backgroundColor: `${colors.orangePeel}20` }}
              >
                {result.coverArt ? (
                  <img
                    src={result.coverArt}
                    alt={result.title}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <Music size={24} style={{ color: colors.darkCyan }} />
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
                    <span
                      className="px-2 py-0.5 rounded-full text-xs"
                      style={{
                        backgroundColor: `${colors.darkCyan}30`,
                        color: colors.darkCyan,
                      }}
                    >
                      {result.genre}
                    </span>
                  </p>
                )}
              </div>

              <Button
                size="sm"
                variant="ghost"
                className="flex items-center gap-1"
                onClick={() => handleApplyResult(result)}
                style={{ color: colors.darkCyan }}
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
            className="mx-auto mb-2"
            style={{ color: colors.orangePeel }}
          />
          <p>No matches found. Try adjusting your search terms.</p>
        </div>
      )}
    </div>
  );
};

export default MusicBrainzSearchTab;
