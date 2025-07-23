import React from "react";
import { Users } from "lucide-react";
import { Song } from "@/types/Song";
import ArtistAccordion from "./ArtistAccordion";

interface Artist {
  name: string;
  songCount: number;
  firstLetter: string;
}

interface ArtistResultsSectionProps {
  artists: Artist[];
  onSongSelect: (song: Song) => void;
  onAddToQueue: (song: Song) => void;
  searchTerm: string;
}

const ArtistResultsSection: React.FC<ArtistResultsSectionProps> = ({
  artists,
  onSongSelect,
  onAddToQueue,
  searchTerm,
}) => {
  // Show section header
  const sectionTitle = searchTerm.trim() ? "Artists" : "Browse All Artists";

  return (
    <div>
      {/* Section Header */}
      <div className="flex items-center gap-3 mb-6">
        <Users size={24} className="text-orange-peel" />
        <h2 className="text-xl font-semibold text-orange-peel">
          {sectionTitle}
        </h2>
      </div>

      {/* Artist Accordion - now a pure presentational component */}
      <ArtistAccordion
        artists={artists}
        onSongSelect={onSongSelect}
        onAddToQueue={onAddToQueue}
      />
    </div>
  );
};

export default ArtistResultsSection;
