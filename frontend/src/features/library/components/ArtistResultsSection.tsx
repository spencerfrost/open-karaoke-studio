import React from "react";
import { Users } from "lucide-react";
import ArtistAccordion from "./ArtistAccordion";
import { useArtists } from "@/hooks/api/useArtists";

interface ArtistResultsSectionProps {
  searchTerm: string;
  expandArtist?: string | null;
}

const ArtistResultsSection: React.FC<ArtistResultsSectionProps> = ({
  searchTerm,
  expandArtist,
}) => {
  const effectiveSearchTerm = expandArtist ? "" : searchTerm;

  const { artists, isLoading } = useArtists({ search: effectiveSearchTerm });

  const sectionTitle = searchTerm.trim() ? "Artists" : "Browse All Artists";

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <Users size={24} className="text-orange-peel" />
        <h2 className="text-xl font-semibold text-orange-peel">
          {sectionTitle}
        </h2>
      </div>

      <ArtistAccordion
        artists={artists}
        isLoading={isLoading}
        expandArtist={expandArtist}
      />
    </div>
  );
};

export default ArtistResultsSection;
