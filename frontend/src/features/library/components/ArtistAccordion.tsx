import React, { useState, useEffect } from "react";
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
  isLoading?: boolean;
  hasNextPage?: boolean;
  isFetchingNextPage?: boolean;
  fetchNextPage?: () => void;
  sentinelRef?: React.RefObject<HTMLDivElement | null>;
  expandArtist?: string | null;
}

const ArtistAccordion: React.FC<ArtistAccordionProps> = ({
  artists = [],
  className = "",
  isLoading = false,
  hasNextPage,
  isFetchingNextPage,
  sentinelRef,
  expandArtist,
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
        const letter = /^\d/.test(artist.firstLetter) ? "#" : artist.firstLetter;
        if (!groups[letter]) {
          groups[letter] = [];
        }
        groups[letter].push(artist);
        return groups;
      },
      {} as Record<string, typeof artists>,
    );
  }, [artists]);

  // Get available letters for navigation, with # always first
  const availableLetters = React.useMemo(() => {
    return Object.keys(groupedArtists).sort((a, b) => {
      if (a === "#") return -1;
      if (b === "#") return 1;
      return a.localeCompare(b);
    });
  }, [groupedArtists]);

  // Handle expandArtist query parameter
  useEffect(() => {
    if (!expandArtist) return;

    const artist = artists.find((a) => a.name === expandArtist);

    if (artist) {
      setExpandedArtists((prev) => {
        const newSet = new Set(prev);
        newSet.add(expandArtist);
        return newSet;
      });

      // Scroll to the artist section after a delay to ensure rendering
      const scrollTimer = setTimeout(() => {
        const element = document.getElementById(`artist-${expandArtist}`);
        if (element) {
          element.scrollIntoView({
            behavior: "smooth",
            block: "center",
          });
        }
      }, 500);

      return () => clearTimeout(scrollTimer);
    }
  }, [expandArtist, artists]);

  // Handle navigation letter click
  const handleLetterClick = (letter: string) => {
    const element = document.getElementById(`artist-section-${letter}`);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  if (isLoading && !artists.length) {
    return (
      <div className={`flex justify-center py-12 ${className}`}>
        <LoadingSpinner size={24} />
      </div>
    );
  }

  if (!artists.length) {
    return (
      <div className={`text-center py-8 text-gray-500 ${className}`}>
        No artists found.
      </div>
    );
  }

  return (
    <div className={`relative ${className}`}>
      <div className="flex gap-2">
        {/* Main content */}
        <div className="flex-1 space-y-6">
          {/* Alphabetical artist sections */}
          {availableLetters.map((letter) => {
            const letterArtists = groupedArtists[letter];
            return (
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
            );
          })}

          {/* Infinite scroll sentinel and loading indicator */}
          {sentinelRef && (
            <div ref={sentinelRef} className="h-4">
              {isFetchingNextPage && (
                <div className="flex justify-center py-4">
                  <LoadingSpinner size={16} />
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
        <div className="sticky top-0 self-start">
          <AlphabeticalNavigation
            availableLetters={availableLetters}
            onLetterClick={handleLetterClick}
          />
        </div>
      </div>
    </div>
  );
};

export default ArtistAccordion;
