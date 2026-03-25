import React, { useState } from "react";
import { ArrowLeft, Loader2, Music, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

import {
  useYoutubeMusicArtist,
  useYoutubeMusicArtistReleases,
} from "@/hooks/api/useYoutubeMusic";
import { YoutubeMusicSearchResult } from "@/types/Youtube";
import { AlbumTracksExpander } from "./AlbumTracksExpander";

const INITIAL_SONGS_COUNT = 5;
const MAX_SONGS_COUNT = 10;

interface ArtistBrowsePanelProps {
  artistId: string;
  artistName: string;
  onBack: () => void;
  onSelectSong: (song: YoutubeMusicSearchResult) => void;
  loadingStates: Record<string, boolean>;
}

export const ArtistBrowsePanel: React.FC<ArtistBrowsePanelProps> = ({
  artistId,
  artistName,
  onBack,
  onSelectSong,
  loadingStates,
}) => {
  const [visibleSongsCount, setVisibleSongsCount] =
    useState(INITIAL_SONGS_COUNT);
  const [loadMoreAlbums, setLoadMoreAlbums] = useState(false);
  const [loadMoreSingles, setLoadMoreSingles] = useState(false);

  const { data, isLoading, error } = useYoutubeMusicArtist(artistId);

  const artistData = data?.data;
  const artist = artistData?.artist;
  const topSongs = artistData?.topSongs || [];
  const albums = artistData?.albums || [];
  const singles = artistData?.singles || [];
  const albumsMore = artistData?.albumsMore;
  const singlesMore = artistData?.singlesMore;

  const { data: moreAlbumsData, isLoading: isLoadingMoreAlbums } =
    useYoutubeMusicArtistReleases(
      artistId,
      albumsMore?.channelId ?? null,
      albumsMore?.params ?? null,
      loadMoreAlbums,
    );
  const { data: moreSinglesData, isLoading: isLoadingMoreSingles } =
    useYoutubeMusicArtistReleases(
      artistId,
      singlesMore?.channelId ?? null,
      singlesMore?.params ?? null,
      loadMoreSingles,
    );

  const displayAlbums = moreAlbumsData?.data ?? albums;
  const displaySingles = moreSinglesData?.data ?? singles;

  // Get artist thumbnail
  const artistThumbnail =
    artist?.thumbnails?.[artist.thumbnails.length - 1]?.url;

  // Calculate visible songs and whether there are more to show
  const visibleTopSongs = topSongs.slice(0, visibleSongsCount);
  const hasMoreSongs = topSongs.length > visibleSongsCount;

  const handleLoadMore = () => {
    setVisibleSongsCount(MAX_SONGS_COUNT);
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <ArtistHeader name={artistName} onBack={onBack} />
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
          <span className="ml-3 text-muted-foreground">Loading artist...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <ArtistHeader name={artistName} onBack={onBack} />
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-destructive">
              Failed to load artist information.
            </p>
            <p className="text-sm text-muted-foreground mt-1">
              Please try again later.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const hasNoContent =
    topSongs.length === 0 && albums.length === 0 && singles.length === 0;

  return (
    <div className="space-y-6">
      {/* Artist Header */}
      <ArtistHeader
        name={artist?.name || artistName}
        thumbnail={artistThumbnail}
        subscribers={artist?.subscribers}
        onBack={onBack}
      />

      {hasNoContent ? (
        <Card>
          <CardContent className="py-8 text-center">
            <Music className="w-12 h-12 mx-auto text-muted-foreground mb-3" />
            <p className="text-muted-foreground">
              No songs or albums found for this artist.
            </p>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Top Songs Section */}
          {topSongs.length > 0 && (
            <section>
              <h3 className="text-lg font-semibold mb-3">Top Songs</h3>
              <div className="space-y-2">
                {visibleTopSongs.map((song) => (
                  <TopSongCard
                    key={song.videoId}
                    song={song}
                    isLoading={loadingStates[song.videoId] || false}
                    onSelect={() => onSelectSong(song)}
                  />
                ))}
              </div>
              {hasMoreSongs && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleLoadMore}
                  className="w-full mt-2 text-muted-foreground hover:text-foreground"
                >
                  Load more
                </Button>
              )}
            </section>
          )}

          {/* Albums Section */}
          {displayAlbums.length > 0 && (
            <section>
              <h3 className="text-lg font-semibold mb-3">Albums</h3>
              <div className="space-y-2">
                {displayAlbums.map((album) => (
                  <AlbumTracksExpander
                    key={album.browseId}
                    album={album}
                    onSelectTrack={onSelectSong}
                    loadingStates={loadingStates}
                  />
                ))}
              </div>
              {albumsMore && (!loadMoreAlbums || isLoadingMoreAlbums) && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setLoadMoreAlbums(true)}
                  disabled={isLoadingMoreAlbums}
                  className="w-full mt-2 text-muted-foreground hover:text-foreground"
                >
                  {isLoadingMoreAlbums ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                      Loading...
                    </>
                  ) : (
                    "Load more albums"
                  )}
                </Button>
              )}
            </section>
          )}

          {/* Singles Section */}
          {displaySingles.length > 0 && (
            <section>
              <h3 className="text-lg font-semibold mb-3">Singles</h3>
              <div className="space-y-2">
                {displaySingles.map((album) => (
                  <AlbumTracksExpander
                    key={album.browseId}
                    album={album}
                    onSelectTrack={onSelectSong}
                    loadingStates={loadingStates}
                  />
                ))}
              </div>
              {singlesMore && (!loadMoreSingles || isLoadingMoreSingles) && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setLoadMoreSingles(true)}
                  disabled={isLoadingMoreSingles}
                  className="w-full mt-2 text-muted-foreground hover:text-foreground"
                >
                  {isLoadingMoreSingles ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                      Loading...
                    </>
                  ) : (
                    "Load more singles"
                  )}
                </Button>
              )}
            </section>
          )}
        </>
      )}
    </div>
  );
};

interface ArtistHeaderProps {
  name: string;
  thumbnail?: string;
  subscribers?: string;
  onBack: () => void;
}

const ArtistHeader: React.FC<ArtistHeaderProps> = ({
  name,
  thumbnail,
  subscribers,
  onBack,
}) => {
  return (
    <div className="flex items-center gap-4">
      <Button variant="ghost" size="icon" onClick={onBack}>
        <ArrowLeft className="w-5 h-5" />
      </Button>

      {/* Artist avatar */}
      <div className="w-12 h-12 rounded-full overflow-hidden flex-shrink-0 bg-muted">
        {thumbnail ? (
          <img
            src={thumbnail}
            alt={name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <User className="w-6 h-6 text-muted-foreground" />
          </div>
        )}
      </div>

      <div className="flex-1 min-w-0">
        <h2 className="text-xl font-bold line-clamp-1">{name}</h2>
        {subscribers && (
          <p className="text-sm text-muted-foreground">
            {subscribers} subscribers
          </p>
        )}
      </div>
    </div>
  );
};

interface TopSongCardProps {
  song: YoutubeMusicSearchResult;
  isLoading: boolean;
  onSelect: () => void;
}

const TopSongCard: React.FC<TopSongCardProps> = ({
  song,
  isLoading,
  onSelect,
}) => {
  const thumbnail = song.thumbnails?.[0]?.url || "";
  const isDisabled = !song.videoId || song.existsInLibrary;

  return (
    <Card className="overflow-hidden py-1 hover:bg-muted/50 transition-colors cursor-pointer">
      <CardContent className="px-3 py-1">
        <div className="flex items-center gap-3">
          {/* Song thumbnail */}
          <div className="w-10 h-10 rounded overflow-hidden flex-shrink-0 bg-muted">
            {thumbnail ? (
              <img
                src={thumbnail}
                alt={song.title}
                className="w-full h-full object-cover"
                loading="lazy"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <Music className="w-4 h-4 text-muted-foreground" />
              </div>
            )}
          </div>

          {/* Song info */}
          <div className="flex-1 min-w-0">
            <p className="font-medium text-sm line-clamp-1">{song.title}</p>
            <p className="text-xs text-muted-foreground line-clamp-1">
              {song.album && `${song.album} • `}
              {song.duration}
            </p>
          </div>

          {/* Add button */}
          <Button
            size="sm"
            onClick={onSelect}
            disabled={isDisabled || isLoading}
            className="flex-shrink-0"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin mr-1" />
                Adding...
              </>
            ) : song.existsInLibrary ? (
              "Added"
            ) : (
              "Add"
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};
