// frontend/src/components/YouTubeMusicSearch.tsx
import { useState } from "react";
import { useYouTubeMusicSearch } from "../hooks/useYouTubeMusic";
import { YouTubeMusicSong } from "../types/YouTubeMusic";
import { useSongs } from "../hooks/useSongs";
import LyricsFetchDialog from "./lyrics/LyricsFetchDialog";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "./ui/card";

export function YouTubeMusicSearch() {
  const [query, setQuery] = useState("");
  const [lyricsDialogOpen, setLyricsDialogOpen] = useState(false);
  const [lyricsDialogData, setLyricsDialogData] = useState<{
    artist: string;
    title: string;
    album?: string;
    duration?: string;
  } | null>(null);
  const { data, isLoading, error } = useYouTubeMusicSearch(query, !!query);
  const { useCreateSong } = useSongs();
  const createSongMutation = useCreateSong();

  const handleAddToLibrary = (song: YouTubeMusicSong) => {
    createSongMutation.mutate(
      {
        title: song.title,
        artist: song.artist,
        album: song.album || "",
        source: "youtube_music",
        videoId: song.videoId,
        duration: song.duration,
      },
      {
        onSuccess: (createdSong) => {
          // Now you have the real song ID
          fetch("/api/songs/download", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              song_id: createdSong.id,
              videoId: song.videoId,
              artist: song.artist,
              title: song.title,
              album: song.album,
            }),
          }).catch(() => {});

          fetch("/api/songs/metadata/auto", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              artist: song.artist,
              title: song.title,
              album: song.album,
              song_id: createdSong.id,
            }),
          }).catch(() => {});

          setLyricsDialogData({
            artist: song.artist,
            title: song.title,
            album: song.album,
            duration: song.duration,
          });
          setLyricsDialogOpen(true);
        },
        onError: (error) => {
          alert("Failed to create song: " + (error?.message || error));
        },
      }
    );
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
                >
                  Add to Library
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
        <LyricsFetchDialog
          open={lyricsDialogOpen}
          onClose={() => setLyricsDialogOpen(false)}
          artist={lyricsDialogData?.artist || ""}
          title={lyricsDialogData?.title || ""}
          album={lyricsDialogData?.album}
          duration={lyricsDialogData?.duration}
          autoSelectBestMatch
        />
      </CardContent>
    </Card>
  );
}
