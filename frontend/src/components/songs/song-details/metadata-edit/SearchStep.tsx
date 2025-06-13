import React from 'react';
import { Song } from '@/types/Song';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Search, Loader2, ExternalLink } from 'lucide-react';

interface SearchStepProps {
  searchArtist: string;
  setSearchArtist: (value: string) => void;
  searchTitle: string;
  setSearchTitle: (value: string) => void;
  searchAlbum: string;
  setSearchAlbum: (value: string) => void;
  onSearch: () => void;
  onKeyPress: (e: React.KeyboardEvent) => void;
  isLoading: boolean;
  song: Song;
}

export const SearchStep: React.FC<SearchStepProps> = ({
  searchArtist,
  setSearchArtist,
  searchTitle,
  setSearchTitle,
  searchAlbum,
  setSearchAlbum,
  onSearch,
  onKeyPress,
  isLoading,
  song
}) => {
  return (
    <div className="space-y-6">
      {/* Current iTunes Data Section */}
      {(song.itunesTrackId || song.itunesArtistId || song.itunesCollectionId) && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Current iTunes Data</CardTitle>
            <CardDescription>
              Administrative information from the currently selected iTunes release
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              {song.itunesTrackId && (
                <div>
                  <Label className="text-xs text-muted-foreground">Track ID</Label>
                  <p className="font-mono">{song.itunesTrackId}</p>
                </div>
              )}
              {song.itunesArtistId && (
                <div>
                  <Label className="text-xs text-muted-foreground">Artist ID</Label>
                  <p className="font-mono">{song.itunesArtistId}</p>
                </div>
              )}
              {song.itunesCollectionId && (
                <div>
                  <Label className="text-xs text-muted-foreground">Collection ID</Label>
                  <p className="font-mono">{song.itunesCollectionId}</p>
                </div>
              )}
            </div>
            {song.itunesPreviewUrl && (
              <div className="pt-2">
                <a 
                  href={song.itunesPreviewUrl} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
                >
                  <ExternalLink className="h-3 w-3" />
                  Preview on iTunes
                </a>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Search Interface */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Search iTunes</CardTitle>
          <CardDescription>
            Modify the search terms below to find the correct iTunes release
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="search-artist">Artist</Label>
              <Input
                id="search-artist"
                value={searchArtist}
                onChange={(e) => setSearchArtist(e.target.value)}
                onKeyPress={onKeyPress}
                placeholder="Enter artist name"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="search-title">Title</Label>
              <Input
                id="search-title"
                value={searchTitle}
                onChange={(e) => setSearchTitle(e.target.value)}
                onKeyPress={onKeyPress}
                placeholder="Enter song title"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="search-album">Album (Optional)</Label>
              <Input
                id="search-album"
                value={searchAlbum}
                onChange={(e) => setSearchAlbum(e.target.value)}
                onKeyPress={onKeyPress}
                placeholder="Enter album name"
              />
            </div>
          </div>
          
          <Button 
            onClick={onSearch}
            disabled={isLoading || (!searchArtist.trim() && !searchTitle.trim())}
            className="w-full md:w-auto"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Searching...
              </>
            ) : (
              <>
                <Search className="h-4 w-4 mr-2" />
                Search iTunes
              </>
            )}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
};
