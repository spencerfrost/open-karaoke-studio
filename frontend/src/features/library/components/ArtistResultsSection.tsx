import React from "react";
import { Users } from "lucide-react";
import ArtistAccordion from "./ArtistAccordion";

interface Artist {
  name: string;
  songCount: number;
  firstLetter: string;
}

interface ArtistResultsSectionProps {
  artists: Artist[];
  searchTerm: string;
  hasNextPage?: boolean;
  isFetchingNextPage?: boolean;
  fetchNextPage?: () => void;
  sentinelRef?: React.RefObject<HTMLDivElement>;
  expandArtist?: string | null;
}

const ArtistResultsSection: React.FC<ArtistResultsSectionProps> = ({
  artists,
  searchTerm,
  hasNextPage,
  isFetchingNextPage,
  fetchNextPage,
  sentinelRef,
  expandArtist,
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
        hasNextPage={hasNextPage}
        isFetchingNextPage={isFetchingNextPage}
        fetchNextPage={fetchNextPage}
        sentinelRef={sentinelRef}
        expandArtist={expandArtist}
      />
    </div>
  );
};

export default ArtistResultsSection;
