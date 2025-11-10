import React, { useState } from "react";
import ArtistSection from "./ArtistSection";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import AlphabeticalNavigation from "./AlphabeticalNavigation";

interface Artist {
  name: string;
  songCount: number;
  firstLetter: string;
}

interface ArtistAccordionProps {
  artists: Artist[];
  className?: string;
  hasNextPage?: boolean;
  isFetchingNextPage?: boolean;
  sentinelRef?: React.RefObject<HTMLDivElement>;
}

const ArtistAccordion: React.FC<ArtistAccordionProps> = ({
  artists = [],
  className = "",
  hasNextPage,
  isFetchingNextPage,
  sentinelRef,
}) => {
  const [expandedArtists, setExpandedArtists] = useState<Set<string>>(
    new Set(),
  );

  const toggleArtist = (artistName: string) => {
    setExpandedArtists((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(artistName)) {
        newSet.delete(artistName);
      } else {
        newSet.add(artistName);
      }
      return newSet;
    });
  };

  // Group artists alphabetically
  const groupedArtists = React.useMemo(() => {
    return artists.reduce(
      (groups, artist) => {
        const letter = artist.firstLetter;
        if (!groups[letter]) {
          groups[letter] = [];
        }
        groups[letter].push(artist);
        return groups;
      },
      {} as Record<string, typeof artists>,
    );
  }, [artists]);

  // Get available letters for navigation
  const availableLetters = React.useMemo(() => {
    return Object.keys(groupedArtists).sort();
  }, [groupedArtists]);

  // Handle navigation letter click
  const handleLetterClick = (letter: string) => {
    const element = document.getElementById(`artist-section-${letter}`);
    if (element) {
      element.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  };

  if (!artists.length) {
    return (
      <div className={`text-center py-8 text-gray-500 ${className}`}>
        No artists found.
      </div>
    );
  }

  return (
    <div className={`relative ${className}`}>
      {/* Mobile horizontal navigation */}
      {availableLetters.length > 0 && (
        <div className="lg:hidden mb-4">
          <AlphabeticalNavigation
            availableLetters={availableLetters}
            onLetterClick={handleLetterClick}
            isMobile={true}
          />
        </div>
      )}

      <div className="flex gap-6">
        {/* Main content */}
        <div className="flex-1 space-y-6">
          {/* Alphabetical artist sections */}
          {Object.entries(groupedArtists).map(([letter, letterArtists]) => (
            <div key={letter} id={`artist-section-${letter}`}>
              <div className="sticky top-0 px-3 py-2 mb-3 font-bold text-lg border-b bg-dark-cyan text-orange-peel border-orange-peel z-10">
                {letter}
              </div>

              <div className="space-y-2">
                {letterArtists.map((artist) => (
                  <ArtistSection
                    key={artist.name}
                    artistName={artist.name}
                    songCount={artist.songCount}
                    isExpanded={expandedArtists.has(artist.name)}
                    onToggle={() => toggleArtist(artist.name)}
                  />
                ))}
              </div>
            </div>
          ))}
          
          {/* Infinite scroll sentinel and loading indicator */}
          {sentinelRef && (
            <div ref={sentinelRef} className="h-4">
              {isFetchingNextPage && (
                <div className="flex justify-center py-4">
                  <LoadingSpinner size="sm" />
                </div>
              )}
              {!hasNextPage && artists.length > 0 && (
                <div className="text-center py-4 text-gray-500 text-sm">
                  All artists loaded ({artists.length} total)
                </div>
              )}
            </div>
          )}
        </div>

        {/* Desktop vertical navigation sidebar */}
        {availableLetters.length > 0 && (
          <div className="hidden lg:block w-12">
            <AlphabeticalNavigation
              availableLetters={availableLetters}
              onLetterClick={handleLetterClick}
              isMobile={false}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default ArtistAccordion;
