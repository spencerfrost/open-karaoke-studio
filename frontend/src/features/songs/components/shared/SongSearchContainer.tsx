import React, { useState, useRef, useEffect } from "react";
import { toast } from "sonner";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";

import { SearchInput } from "./SearchInput";
import { SearchTabs } from "./SearchTabs";
import { SearchResults } from "./SearchResults";
import { YoutubeMusicResultCard } from "../YoutubeMusicResultCard";
import { createLogger } from "@/lib/logger";

const logger = createLogger("component:song-search");
import { YouTubeResultCard } from "../YoutubeVideoResultCard";
import { ArtistResultCard } from "../ArtistResultCard";
import { ArtistBrowsePanel } from "../artist-browse";

import { useYoutubeMusicSearch } from "@/hooks/api/useYoutubeMusic";
import { useYoutubeVideoSearch } from "@/hooks/useYoutubeVideoSearch";
import { useSongCreation, SongInput } from "../../hooks/useSongCreation";

import { SongSearchContainerProps, SearchSource } from "./types";
import {
  YoutubeMusicSearchResult,
  YoutubeVideoSearchResult,
} from "@/types/Youtube";

// Data mappers to convert search results to unified SongInput
const mapYoutubeMusicToSongInput = (
  result: YoutubeMusicSearchResult,
): SongInput => ({
  title: result.title,
  artist: result.artist,
  album: result.album,
  videoId: result.videoId,
  source: "youtube_music",
  url: `https://www.youtube.com/watch?v=${result.videoId}`,
  duration: result.duration,
  thumbnail: result.thumbnails[0]?.url || "",
});

const mapYouTubeToSongInput = (
  result: YoutubeVideoSearchResult,
): SongInput => ({
  title: result.title,
  artist: result.channel,
  album: "",
  videoId: result.id,
  source: "youtube",
  url: result.url,
  duration: result.duration.toString(),
  thumbnail: result.thumbnail,
});

// Artist browse state type
interface BrowsingArtist {
  id: string;
  name: string;
}

/**
 * Unified search container that replaces the side-by-side search components
 * Provides tabbed interface for YouTube Music and YouTube search
 */
export const SongSearchContainer: React.FC<SongSearchContainerProps> = ({
  className = "",
  initialQuery = "",
  autoBrowseArtist = false,
}) => {
  const [query, setQuery] = useState(initialQuery);
  const [activeSource, setActiveSource] =
    useState<SearchSource>("youtube-music");
  const [browsingArtist, setBrowsingArtist] = useState<BrowsingArtist | null>(
    null,
  );

  const hasAttemptedAutoBrowse = useRef(false);

  // Debounce the query to avoid excessive API calls while typing
  const debouncedQuery = useDebouncedValue(query, 400);

  // Use existing search hooks
  const youtubeMusicSearch = useYoutubeMusicSearch(
    debouncedQuery,
    activeSource === "youtube-music" && !!debouncedQuery,
  );

  const youtubeSearch = useYoutubeVideoSearch({
    query: debouncedQuery,
    enabled: activeSource === "youtube" && !!debouncedQuery,
  });

  // Auto-browse: when navigating from library with browseArtist=true,
  // automatically open the first matching artist result
  useEffect(() => {
    if (
      autoBrowseArtist &&
      !hasAttemptedAutoBrowse.current &&
      !browsingArtist &&
      !youtubeMusicSearch.isLoading &&
      youtubeMusicSearch.data
    ) {
      hasAttemptedAutoBrowse.current = true;
      const artists = youtubeMusicSearch.data.artists || [];
      if (artists.length > 0) {
        const firstArtist = artists[0];
        setBrowsingArtist({ id: firstArtist.browseId, name: firstArtist.name });
      }
    }
  }, [
    autoBrowseArtist,
    browsingArtist,
    youtubeMusicSearch.isLoading,
    youtubeMusicSearch.data,
  ]);

  // Single song creation hook for both flows
  const songCreation = useSongCreation();

  const handleSearch = (searchQuery: string) => {
    setQuery(searchQuery);
    // Clear artist browse when searching
    setBrowsingArtist(null);
  };

  const handleArtistClick = (artistId: string, artistName: string) => {
    setBrowsingArtist({ id: artistId, name: artistName });
  };

  const handleBackFromArtist = () => {
    setBrowsingArtist(null);
  };

  const handleYoutubeMusicSelect = async (result: YoutubeMusicSearchResult) => {
    try {
      logger.debug("YouTube Music result selected", {
        videoId: result.videoId,
        title: result.title,
        existsInLibrary: result.existsInLibrary,
        status: songCreation.getSubmissionStatus(result.videoId),
      });
      const songInput = mapYoutubeMusicToSongInput(result);
      await songCreation.createSong(songInput);
    } catch (error) {
      logger.error("Failed to create YouTube Music song:", error);
      toast.error("Failed to add song");
    }
  };

  const handleYouTubeSelect = async (result: YoutubeVideoSearchResult) => {
    try {
      logger.debug("YouTube result selected", {
        videoId: result.id,
        title: result.title,
        status: songCreation.getSubmissionStatus(result.id),
      });
      const songInput = mapYouTubeToSongInput(result);
      await songCreation.createSong(songInput);
    } catch (error) {
      logger.error("Failed to create YouTube song:", error);
      toast.error("Failed to add song");
    }
  };

  // Get results and counts
  const artistResults = youtubeMusicSearch.data?.artists || [];
  const songResults = youtubeMusicSearch.data?.songs || [];
  const youtubeResults = youtubeSearch.data || [];

  const counts = {
    "youtube-music": artistResults.length + songResults.length,
    youtube: youtubeResults.length,
  };

  // When browsing an artist, show the artist panel instead of search results
  if (browsingArtist) {
    return (
      <div className={`space-y-6 ${className}`}>
        <Card>
          <CardHeader>
            <CardTitle>Add Songs</CardTitle>
            <CardDescription>
              Browse songs from {browsingArtist.name}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ArtistBrowsePanel
              artistId={browsingArtist.id}
              artistName={browsingArtist.name}
              onBack={handleBackFromArtist}
              onSelectSong={handleYoutubeMusicSelect}
              getSubmissionStatus={songCreation.getSubmissionStatus}
            />
          </CardContent>
        </Card>

      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      <Card>
        <CardHeader>
          <CardTitle>Add Songs</CardTitle>
          <CardDescription>
            Search and add songs from YouTube Music or YouTube videos to your
            karaoke library
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <SearchInput
            query={query}
            onSearch={handleSearch}
            placeholder="Search for songs, artists, or albums..."
          />
          <SearchTabs
            activeSource={activeSource}
            onSourceChange={setActiveSource}
            counts={counts}
          />

          {activeSource === "youtube-music" && (
            <div className="space-y-6">
              {/* Artists Section - Only if results exist */}
              {artistResults.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                    Artists ({artistResults.length})
                  </h3>
                  <div className="grid grid-cols-1 gap-2">
                    {artistResults.map((artist) => (
                      <ArtistResultCard
                        key={artist.browseId}
                        result={artist}
                        onArtistClick={handleArtistClick}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Songs Section */}
              {songResults.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                    Songs ({songResults.length})
                  </h3>
                  <SearchResults
                    results={songResults}
                    isLoading={youtubeMusicSearch.isLoading}
                    error={youtubeMusicSearch.error}
                    onSelect={handleYoutubeMusicSelect}
                    getSubmissionStatus={songCreation.getSubmissionStatus}
                    resultCardComponent={YoutubeMusicResultCard}
                    keyExtractor={(result) => result.videoId}
                    emptyMessage="Search YouTube Music"
                    emptyDescription="Find official tracks with high-quality audio and reliable metadata."
                    onArtistClick={handleArtistClick}
                  />
                </div>
              )}

              {/* Empty State - When both are empty */}
              {artistResults.length === 0 &&
                songResults.length === 0 &&
                !youtubeMusicSearch.isLoading && (
                  <div className="text-center py-8 text-muted-foreground">
                    <p className="font-medium">Search YouTube Music</p>
                    <p className="text-sm">
                      Find official tracks with high-quality audio and reliable
                      metadata.
                    </p>
                  </div>
                )}
            </div>
          )}

          {activeSource === "youtube" && (
            <SearchResults
              results={youtubeResults}
              isLoading={youtubeSearch.isLoading}
              error={youtubeSearch.error}
              onSelect={handleYouTubeSelect}
              getSubmissionStatus={songCreation.getSubmissionStatus}
              resultCardComponent={YouTubeResultCard}
              keyExtractor={(result) => result.id}
              emptyMessage="Search YouTube"
              emptyDescription="Find any video content when official tracks aren't available."
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
};
