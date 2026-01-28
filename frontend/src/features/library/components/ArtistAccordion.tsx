import React, { useState, useEffect, useRef } from "react";
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
  fetchNextPage?: () => void;
  sentinelRef?: React.RefObject<HTMLDivElement>;
  expandArtist?: string | null;
}

const ArtistAccordion: React.FC<ArtistAccordionProps> = ({
  artists = [],
  className = "",
  hasNextPage,
  isFetchingNextPage,
  fetchNextPage,
  sentinelRef,
  expandArtist,
}) => {
  const [expandedArtists, setExpandedArtists] = useState<Set<string>>(
    new Set(),
  );
  const [pendingLetter, setPendingLetter] = useState<string | null>(null);
  const loadingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

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

  // Watch for pending letter to become available
  useEffect(() => {
    if (pendingLetter && availableLetters.includes(pendingLetter)) {
      // Letter is now loaded, navigate to it
      const element = document.getElementById(
        `artist-section-${pendingLetter}`,
      );
      if (element) {
        element.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
      setPendingLetter(null);
      if (loadingTimeoutRef.current) {
        clearTimeout(loadingTimeoutRef.current);
        loadingTimeoutRef.current = null;
      }
    }
  }, [pendingLetter, availableLetters]);

  // Handle expandArtist query parameter
  useEffect(() => {
    if (!expandArtist) return;

    const artist = artists.find((a) => a.name === expandArtist);

    if (artist) {
      // Artist is loaded, expand it
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

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (loadingTimeoutRef.current) {
        clearTimeout(loadingTimeoutRef.current);
      }
    };
  }, []);

  // Handle navigation letter click
  const handleLetterClick = (letter: string) => {
    const isAvailable = availableLetters.includes(letter);

    if (isAvailable) {
      // Letter is already loaded, navigate immediately
      const element = document.getElementById(`artist-section-${letter}`);
      if (element) {
        element.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    } else if (hasNextPage && fetchNextPage) {
      // Letter not loaded yet, trigger loading
      setPendingLetter(letter);

      // Scroll to bottom to trigger sentinel
      if (sentinelRef?.current) {
        sentinelRef.current.scrollIntoView({
          behavior: "smooth",
          block: "end",
        });
      }

      // Trigger initial page load
      fetchNextPage();

      // Set up repeated loading until letter appears or timeout
      const startLoading = () => {
        const loadInterval = setInterval(() => {
          if (availableLetters.includes(letter) || !hasNextPage) {
            clearInterval(loadInterval);
            return;
          }
          fetchNextPage();
        }, 1000);

        // Timeout after 30 seconds
        loadingTimeoutRef.current = setTimeout(() => {
          clearInterval(loadInterval);
          setPendingLetter(null);
          console.warn(`Timed out waiting for letter ${letter}`);
        }, 30000);
      };

      startLoading();
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
      <div className="lg:hidden mb-4">
        <AlphabeticalNavigation
          availableLetters={availableLetters}
          onLetterClick={handleLetterClick}
          pendingLetter={pendingLetter}
          hasNextPage={hasNextPage}
          isMobile={true}
        />
      </div>

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
        <div className="hidden lg:block w-12">
          <AlphabeticalNavigation
            availableLetters={availableLetters}
            onLetterClick={handleLetterClick}
            pendingLetter={pendingLetter}
            hasNextPage={hasNextPage}
            isMobile={false}
          />
        </div>
      </div>
    </div>
  );
};

export default ArtistAccordion;
