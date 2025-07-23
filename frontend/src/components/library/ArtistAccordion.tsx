import React, { useState } from "react";
import ArtistSection from "./ArtistSection";
import { Song } from "@/types/Song";

interface Artist {
  name: string;
  songCount: number;
  firstLetter: string;
}

interface ArtistAccordionProps {
  artists: Artist[];
  onSongSelect?: (song: Song) => void;
  onAddToQueue?: (song: Song) => void;
  className?: string;
}

const ArtistAccordion: React.FC<ArtistAccordionProps> = ({
  artists = [],
  onSongSelect,
  onAddToQueue,
  className = "",
}) => {
  const [expandedArtists, setExpandedArtists] = useState<Set<string>>(new Set());

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
      {} as Record<string, typeof artists>
    );
  }, [artists]);

  if (!artists.length) {
    return (
      <div className={`text-center py-8 text-gray-500 ${className}`}>
        No artists found.
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Alphabetical artist sections */}
      {Object.entries(groupedArtists).map(([letter, letterArtists]) => (
        <div key={letter}>
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
                onSongSelect={onSongSelect}
                onAddToQueue={onAddToQueue}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

export default ArtistAccordion;
