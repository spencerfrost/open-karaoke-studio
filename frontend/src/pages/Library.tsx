import React, { useState } from "react";
import { useArtists } from "@/hooks/api/useArtists";
import { Filter, Music } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import LibrarySearchInput from "../components/library/LibrarySearchInput";
import SongResultsSection from "../components/library/SongResultsSection";
import ArtistResultsSection from "../components/library/ArtistResultsSection";
import RecentlyAddedSongs from "../components/library/RecentlyAddedSongs/RecentlyAddedSongs";
import { Song } from "@/types/Song";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useSongs as useSongsHook } from "@/hooks/api/useSongs";
import JobsQueue from "@/components/jobs-queue";
import { useSessionStore } from "@/stores/sessionStore";
import { toast } from "sonner";

const LibraryPage: React.FC = () => {
  const navigate = useNavigate();

  // State
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [sessionCode, setSessionCode] = useState("");

  // Session store
  const { displayCode, joinSession } = useSessionStore();

  // Check if user is in a session
  const isInSession = !!displayCode;

  // Song search (paginated, not infinite)
  const { useSongs } = useSongsHook();

  // Use appropriate parameters based on whether we're searching or browsing
  const songsParams = searchTerm.trim()
    ? {
        // Search parameters - the backend should handle this in useSongs
        q: searchTerm,
        limit: 24,
        offset: 0,
        sort: "relevance",
        direction: "desc",
      }
    : {
        limit: 24,
        offset: 0,
        sort_by: "date_added",
        direction: "desc",
      };

  const songsQuery = useSongs(songsParams);

  // Artist search (fetch all matching artists, up to 200)
  const { artists, isLoading: artistsLoading } = useArtists({
    search: searchTerm,
    limit: 200,
  });

  // Handlers
  const handleSongSelect = (song: Song) => {
    navigate(`/player/${song.id}`);
  };

  const handleAddToQueue = (song: Song) => {
    navigate("/queue", { state: { songId: song.id } });
  };

  const handleJoinSession = async () => {
    if (sessionCode.length === 4) {
      try {
        await joinSession(sessionCode, "controller");
        toast.success("Joined session successfully!");
      } catch (error) {
        console.error("Failed to join session:", error);
        toast.error("Failed to join session. Please check the code and try again.");
      }
    } else {
      toast.error("Please enter a 4-character session code.");
    }
  };

  // hasSearch logic
  const hasSearch = searchTerm && searchTerm.trim().length > 0;

  return (
    <AppLayout>
      {!isInSession ? (
        <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6">
          <h1 className="text-4xl font-bold text-orange-peel text-center">
            Join a Session
          </h1>
          <p className="text-xl text-center text-muted-foreground max-w-md">
            Enter the 4-character session code to browse and add songs to the queue!
          </p>
          <div className="flex flex-col items-center gap-4 w-full max-w-sm">
            <input
              type="text"
              placeholder="ABCD"
              value={sessionCode}
              onChange={(e) => setSessionCode(e.target.value.toUpperCase())}
              className="w-full px-4 py-3 text-center text-2xl font-mono font-bold uppercase bg-background border-2 border-orange-peel rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-peel"
              maxLength={4}
            />
            <button
              onClick={handleJoinSession}
              className="w-full px-6 py-3 bg-orange-peel text-background font-semibold rounded-lg hover:bg-orange-peel/90 transition-colors disabled:opacity-50"
              disabled={sessionCode.length !== 4}
            >
              Join Session
            </button>
          </div>
        </div>
      ) : (
        <div className="mb-6">
          {/* Search Input */}
          <div className="mb-6">
            <LibrarySearchInput
              searchTerm={searchTerm}
              onSearchChange={setSearchTerm}
              isLoading={songsQuery.isLoading || artistsLoading}
              placeholder="Search songs and artists..."
              className="w-full max-w-xl mx-auto"
            />
            {/* <Button
              variant="outline"
              onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
              className="border-orange-peel text-orange-peel"
            >
              <Filter size={16} className="mr-2" />
              Advanced Filters
            </Button> */}
          </div>

          {/* Advanced Filters Panel */}
          {showAdvancedFilters && (
            <div className="mb-6 p-4 border border-orange-peel rounded-lg">
              <div className="text-sm opacity-60 mb-2">
                Advanced filtering options coming soon...
              </div>
              {/* TODO: Add genre, year, source filters here */}
            </div>
          )}

          <div className="space-y-8">
            {!hasSearch ? (
              <RecentlyAddedSongs
                onSongSelect={handleSongSelect}
                songsPerPage={12}
                maxSongs={48}
                animated={true}
                sessionId={displayCode}
              />
            ) : (
              <SongResultsSection
                songs={songsQuery.data || []}
                hasNextPage={false} // Pagination can be added later
                isFetchingNextPage={false}
                fetchNextPage={() => {}}
                onSongSelect={handleSongSelect}
                searchTerm={searchTerm}
                sessionId={displayCode}
              />
            )}
            {/* Artist Results Section - Always visible for browsing */}
            <ArtistResultsSection
              artists={artists}
              onSongSelect={handleSongSelect}
              onAddToQueue={handleAddToQueue}
              searchTerm={searchTerm}
              sessionId={displayCode}
            />
          </div>
        </div>
      )}
      <JobsQueue />
    </AppLayout>
  );
};

export default LibraryPage;
