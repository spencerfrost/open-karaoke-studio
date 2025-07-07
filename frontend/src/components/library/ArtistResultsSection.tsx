import React from "react";
import { Users } from "lucide-react";
import { Song } from "@/types/Song";
import InfiniteArtistAccordion from "./InfiniteArtistAccordion";

interface Artist {
  name: string;
  songCount: number;
  firstLetter: string;
}

interface ArtistResultsSectionProps {
  artists: Artist[]; // Not used directly, but kept for consistency
  hasNextPage: boolean; // Not used - InfiniteArtistAccordion handles its own pagination
  isFetchingNextPage: boolean; // Not used - InfiniteArtistAccordion handles its own pagination
  fetchNextPage: () => void; // Not used - InfiniteArtistAccordion handles its own pagination
  onSongSelect: (song: Song) => void;
  onAddToQueue: (song: Song) => void;
  searchTerm: string;
}

const ArtistResultsSection: React.FC<ArtistResultsSectionProps> = ({
  onSongSelect,
  onAddToQueue,
  searchTerm,
  // Unused props (handled internally by InfiniteArtistAccordion):
  // artists, hasNextPage, isFetchingNextPage, fetchNextPage
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
        {/* Note: Artist count is shown by InfiniteArtistAccordion internally */}
      </div>

      {/* Artist Accordion - Reuse existing infinite scrolling logic */}
      <InfiniteArtistAccordion
        searchTerm={searchTerm}
        onSongSelect={onSongSelect}
        onAddToQueue={onAddToQueue}
      />
    </div>
  );
};

export default ArtistResultsSection;
