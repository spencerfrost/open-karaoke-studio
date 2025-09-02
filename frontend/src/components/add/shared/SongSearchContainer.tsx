import React, { useState } from "react";
import { toast } from "sonner";
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
import { YoutubeMusicResultCard } from "../youtube-music/YoutubeMusicResultCard";
import { YouTubeResultCard } from "../youtube-video/YoutubeVideoResultCard";
import { AddSongDialog } from "../AddSongDialog";

import { useYoutubeMusicSearch } from "@/hooks/api/useYoutubeMusic";
import { useYoutubeVideoSearch } from "@/hooks/useYoutubeVideoSearch";
import { useSongCreation, SongInput } from "@/hooks/useSongCreation";
import { useAddSongDialog } from "@/hooks/useAddSongDialog";

import { SongSearchContainerProps, SearchSource } from "./types";
import { YoutubeMusicSearchResult } from "../youtube-music";
import { YoutubeVideoSearchResult } from "../youtube-video";

// Data mappers to convert search results to unified SongInput
const mapYoutubeMusicToSongInput = (result: YoutubeMusicSearchResult): SongInput => ({
  title: result.title,
  artist: result.artist,
  album: result.album,
  videoId: result.videoId,
  source: "youtube_music",
  url: `https://www.youtube.com/watch?v=${result.videoId}`,
  duration: result.duration,
  thumbnail: result.thumbnails[0]?.url || "",
});

const mapYouTubeToSongInput = (result: YoutubeVideoSearchResult): SongInput => ({
  title: result.title,
  artist: result.uploader,
  album: "",
  videoId: result.id,
  source: "youtube",
  url: result.url,
  duration: result.duration.toString(),
  thumbnail: result.thumbnail,
});

/**
 * Unified search container that replaces the side-by-side search components
 * Provides tabbed interface for YouTube Music and YouTube search
 */
export const SongSearchContainer: React.FC<SongSearchContainerProps> = ({
  className = "",
}) => {
  const [query, setQuery] = useState("");
  const [activeSource, setActiveSource] =
    useState<SearchSource>("youtube-music");

  // Use existing search hooks
  const youtubeMusicSearch = useYoutubeMusicSearch(
    query,
    activeSource === "youtube-music" && !!query,
  );

  const youtubeSearch = useYoutubeVideoSearch({
    query,
    enabled: activeSource === "youtube" && !!query,
  });

  // Single song creation hook for both flows
  const songCreation = useSongCreation();

  // Dialog management
  const dialog = useAddSongDialog();

  // Loading states for both result types
  const youtubeMusicLoadingStates: Record<string, boolean> = 
    Object.fromEntries(
      (youtubeMusicSearch.data?.results || []).map((result: YoutubeMusicSearchResult) => [
        result.videoId, 
        songCreation.isAdding && songCreation.currentSong?.videoId === result.videoId
      ])
    );

  const youtubeLoadingStates: Record<string, boolean> = 
    Object.fromEntries(
      (youtubeSearch.data || []).map((result: YoutubeVideoSearchResult) => [
        result.id, 
        songCreation.isAdding && songCreation.currentSong?.videoId === result.id
      ])
    );

  const handleSearch = (searchQuery: string) => {
    setQuery(searchQuery);
  };

  const handleYoutubeMusicSelect = async (result: YoutubeMusicSearchResult) => {
    try {
      const songInput = mapYoutubeMusicToSongInput(result);
      await songCreation.createSong(songInput);
      dialog.openDialog();
    } catch (error) {
      console.error("Failed to create YouTube Music song:", error);
      toast.error("Failed to add song");
    }
  };

  const handleYouTubeSelect = async (result: YoutubeVideoSearchResult) => {
    try {
      const songInput = mapYouTubeToSongInput(result);
      await songCreation.createSong(songInput);
      dialog.openDialog();
    } catch (error) {
      console.error("Failed to create YouTube song:", error);
      toast.error("Failed to add song");
    }
  };

  // Get results and counts
  const youtubeMusicResults = youtubeMusicSearch.data?.results || [];
  const youtubeResults = youtubeSearch.data || [];

  const counts = {
    "youtube-music": youtubeMusicResults.length,
    youtube: youtubeResults.length,
  };

  return (
    <div className={`space-y-6 ${className}`}>
      <Card>
        <CardHeader>
          <CardTitle>Add Songs</CardTitle>
          <CardDescription>
            Search and add songs from YouTube Music or YouTube videos to your karaoke library
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
            <SearchResults
              results={youtubeMusicResults}
              isLoading={youtubeMusicSearch.isLoading}
              error={youtubeMusicSearch.error}
              onSelect={handleYoutubeMusicSelect}
              loadingStates={youtubeMusicLoadingStates}
              resultCardComponent={YoutubeMusicResultCard}
              keyExtractor={(result) => result.videoId}
              emptyMessage="Search YouTube Music"
              emptyDescription="Find official tracks with high-quality audio and reliable metadata."
            />
          )}

          {activeSource === "youtube" && (
            <SearchResults
              results={youtubeResults}
              isLoading={youtubeSearch.isLoading}
              error={youtubeSearch.error}
              onSelect={handleYouTubeSelect}
              loadingStates={youtubeLoadingStates}
              resultCardComponent={YouTubeResultCard}
              keyExtractor={(result) => result.id}
              emptyMessage="Search YouTube"
              emptyDescription="Find any video content when official tracks aren't available."
            />
          )}
        </CardContent>
      </Card>

      <AddSongDialog
        songCreation={songCreation}
        dialog={dialog}
      />
    </div>
  );
};