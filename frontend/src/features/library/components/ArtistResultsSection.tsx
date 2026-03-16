import React from "react";
import { Users } from "lucide-react";
import ArtistAccordion from "./ArtistAccordion";
import { useInfiniteArtists } from "@/hooks/api/useInfiniteLibraryBrowsing";
import { useInfiniteScroll } from "@/hooks/useInfiniteScroll";

interface ArtistResultsSectionProps {
  searchTerm: string;
  expandArtist?: string | null;
}

const ArtistResultsSection: React.FC<ArtistResultsSectionProps> = ({
  searchTerm,
  expandArtist,
}) => {
  const effectiveSearchTerm = expandArtist ? "" : searchTerm;

  const { artists, hasNextPage, isFetchingNextPage, fetchNextPage, isLoading } =
    useInfiniteArtists(effectiveSearchTerm, 200);

  const sentinelRef = useInfiniteScroll({
    loading: isFetchingNextPage,
    hasMore: hasNextPage,
    onLoadMore: fetchNextPage,
    threshold: 0.1,
    rootMargin: "100px",
  });

  // When expandArtist is set, keep fetching pages until the artist is found
  React.useEffect(() => {
    if (
      expandArtist &&
      !artists.find((a) => a.name === expandArtist) &&
      hasNextPage &&
      !isFetchingNextPage
    ) {
      fetchNextPage();
    }
  }, [expandArtist, artists, hasNextPage, isFetchingNextPage, fetchNextPage]);

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
