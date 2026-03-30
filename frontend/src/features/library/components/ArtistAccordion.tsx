import React, { useState, useEffect } from "react";
import ArtistSection from "./ArtistSection";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import AlphabeticalIndexBar from "./AlphabeticalIndexBar";
import AlphabeticalNavigation from "./AlphabeticalNavigation";
import { useAuthStore } from "@/stores/authStore";
import { Artist } from "@/hooks/api/useArtists";

interface ArtistAccordionProps {
  artists: Artist[];
  className?: string;
  isLoading?: boolean;
  expandArtist?: string | null;
}

const ArtistAccordion: React.FC<ArtistAccordionProps> = ({
  artists = [],
  className = "",
  isLoading = false,
  expandArtist,
}) => {
  const [expandedArtists, setExpandedArtists] = useState<Set<string>>(
    new Set(),
  );
  const { user } = useAuthStore();
  const isAdmin = !!user?.isAdmin;

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
                <div className={`sticky top-0 px-3 py-2 mb-3 z-10
                  flex items-center justify-center
                  rounded-full w-12 h-12
                  font-bold text-lg bg-dark-cyan/50 text-orange-peel
                  `
                }>
                  {letter}
                </div>

                <div className="space-y-2">
                  {letterArtists.map((artist) => (
                    <ArtistSection
                      key={artist.name}
                      artist={artist}
                      isExpanded={expandedArtists.has(artist.name)}
                      onToggle={() => toggleArtist(artist.name)}
                      isAdmin={isAdmin}
                    />
                  ))}
                </div>
              </div>
            );
          })}

        </div>

        {/* Mobile: full-height touch index bar */}
        <div className="sticky top-0 h-screen md:hidden">
          <AlphabeticalIndexBar
            availableLetters={availableLetters}
            onLetterClick={handleLetterClick}
          />
        </div>

        {/* Desktop: compact button sidebar */}
        <div className="sticky top-0 h-[calc(100vh-6rem)] hidden md:block">
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
