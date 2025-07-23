// frontend/src/components/YouTubeMusicSearch.tsx
import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import { useYouTubeMusicSearch } from "../../hooks/useYouTubeMusic";
import { YouTubeMusicSong } from "../../types/YouTubeMusic";
import { useSongs } from "../../hooks/useSongs";
import { useState } from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "../ui/card";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "../ui/dialog";
import { LyricsResults } from "../forms";
import { useLyricsSearch } from "../../hooks/useLyrics";
import { useYoutubeDownloadMutation } from "@/hooks/useYoutube";
import type { LyricsOption } from "@/components/forms";
import { toast } from "sonner";
import { Song } from "@/types/Song";

export function YouTubeMusicSearch() {
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebouncedValue(query, 1000);
  // --- New state for stepper/dialog and loading ---
  const [selectedSong, setSelectedSong] = useState<YouTubeMusicSong | null>(
    null
  );
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [createdSong, setCreatedSong] = useState<Song | null>(null);
  const [isAdding, setIsAdding] = useState(false);

  const {
    data: lyricsOptions,
    loading: isLoadingLyrics,
    search: fetchLyrics,
  } = useLyricsSearch();

  const [selectedLyrics, setSelectedLyrics] = useState<LyricsOption | null>(
    null
  );
  const { data, isLoading, error } = useYouTubeMusicSearch(
    debouncedQuery,
    !!debouncedQuery
  );
  const { useCreateSong } = useSongs();
  const createSongMutation = useCreateSong();

  const { useUpdateSong } = useSongs();
  const updateSongMutation = useUpdateSong();

  const handleConfirmLyrics = () => {
    if (createdSong && selectedLyrics) {
      updateSongMutation.mutate({
        id: createdSong.id,
        plainLyrics: selectedLyrics.plainLyrics,
        syncedLyrics: selectedLyrics.syncedLyrics,
      });
    }
    setIsDialogOpen(false);
    setSelectedSong(null);
    setCreatedSong(null);
    setSelectedLyrics(null);
  };

  function handleCreateSong(song: YouTubeMusicSong) {
    createSongMutation.mutate(
      {
        title: song.title,
        artist: song.artist,
        album: song.album || "",
        source: "youtube_music",
        videoId: song.videoId,
      },
      {
        onSuccess: (createdSong) => {
          setCreatedSong(createdSong);
          setIsDialogOpen(true);
          setIsAdding(false);
          fetchLyrics({
            artist: song.artist,
            title: song.title,
            album: song.album,
          });
          downloadFromYouTube(createdSong.id, song);
          getMetadata(createdSong.id, song);
        },
        onError: (error) => {
          setIsAdding(false);
          toast.error("Failed to create song: " + (error?.message || error));
        },
      }
    );
  }

  function downloadFromYouTube(song_id: string, song: YouTubeMusicSong) {
    youtubeDownloadMutation.mutate({
      video_id: song.videoId,
      title: song.title,
      artist: song.artist,
      album: song.album,
      song_id: song_id,
    });
  }

  function getMetadata(song_id: string, song: YouTubeMusicSong) {
    // Fetch metadata from YouTube Music API
    fetch("/api/songs/metadata/auto", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        artist: song.artist,
        title: song.title,
        album: song.album,
        song_id: song_id,
      }),
    }).catch(() => {});
  }

  const youtubeDownloadMutation = useYoutubeDownloadMutation({
    onSuccess: () => {
      toast.success("YouTube download started in background");
    },
    onError: (error) => {
      toast.error(`Failed to start download: ${error.message}`);
    },
  });

  const handleAddToLibrary = (song: YouTubeMusicSong) => {
    setIsAdding(true);
    setSelectedSong(song);
    setSelectedLyrics(null);
    fetchLyrics({
      artist: song.artist,
      title: song.title,
      album: song.album,
    });
    handleCreateSong(song);
  };

  return (
    <Card className="overflow-hidden bg-card/80 pb-0 gap-4">
      <CardHeader>
        <CardTitle className="text-lg font-semibold">
          YouTube Music Search
        </CardTitle>
        <CardDescription className="text-sm text-gray-500">
          Search for official audio tracks on YouTube Music.
        </CardDescription>
      </CardHeader>

      <CardContent>
        <input
          className="w-full border rounded px-3 py-2 mb-4 focus:outline-none focus:ring"
          type="text"
          placeholder="Search for official audio..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        {isLoading && <div className="text-center py-4">Loading...</div>}
        {error && <div className="text-red-500 py-2">{error.message}</div>}
        {data && data.results.length > 0 && (
          <ul className="divide-y divide-gray-200">
            {data.results.map((song: YouTubeMusicSong) => (
              <li key={song.videoId} className="py-3 flex items-center">
                {song.thumbnails?.[0]?.url && (
                  <img
                    src={song.thumbnails[0].url}
                    alt={song.title}
                    className="w-12 h-12 rounded mr-3 object-cover"
                  />
                )}
                <div className="flex-1">
                  <div className="font-medium">{song.title}</div>
                  <div className="text-sm text-gray-600">
                    {song.artist} &bull; {song.duration}
                  </div>
                  {song.album && (
                    <div className="text-xs text-gray-400">
                      Album: {song.album}
                    </div>
                  )}
                </div>
                <button
                  className="ml-4 px-3 py-1 rounded bg-blue-600 text-white"
                  onClick={() => handleAddToLibrary(song)}
                  disabled={isAdding && selectedSong?.videoId === song.videoId}
                >
                  {isAdding && selectedSong?.videoId === song.videoId ? (
                    <>
                      <span className="loader mr-2" /> Processing...
                    </>
                  ) : (
                    "Add to Library"
                  )}
                </button>
              </li>
            ))}
          </ul>
        )}
        {data && data.results.length === 0 && query && !isLoading && (
          <div className="text-center text-gray-500 py-4">
            No official audio found.
          </div>
        )}
      </CardContent>

      {selectedSong && createdSong && (
        <Dialog
          open={isDialogOpen}
          onOpenChange={(open) => {
            if (!open) {
              setIsDialogOpen(false);
              setSelectedSong(null);
              setCreatedSong(null);
              setSelectedLyrics(null);
            }
          }}
        >
          <DialogContent className="sm:max-w-[700px] max-h-[90vh] flex flex-col">
            <DialogHeader className="flex-shrink-0">
              <DialogTitle>Add Song to Library</DialogTitle>
              <DialogDescription>
                Adding: <strong>{selectedSong.title}</strong>
              </DialogDescription>
            </DialogHeader>
            <div className="flex-1 overflow-y-auto">
              <LyricsResults
                isLoading={isLoadingLyrics}
                options={lyricsOptions || []}
                selectedOption={selectedLyrics}
                onSelectionChange={(lyrics) => setSelectedLyrics(lyrics)}
                youtubeMusicDurationSeconds={selectedSong.duration}
              />
            </div>
            <div className="flex justify-end pt-4">
              <button
                className="px-4 py-2 bg-blue-600 text-white rounded"
                onClick={() => handleConfirmLyrics()}
                disabled={!selectedLyrics}
              >
                Confirm
              </button>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </Card>
  );
}
