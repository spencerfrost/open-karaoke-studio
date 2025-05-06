import React, { useEffect, useState, useRef } from "react";
import { Play, Pause, Volume2, VolumeX } from "lucide-react";
import {
  getSongById,
  updateSongMetadata,
  getAudioUrl,
} from "@/services/songService";
import { fetchLyrics } from "@/services/youtubeService";
import { Song } from "@/types/Song";
import SyncedLyricsDisplay from "@/components/player/SyncedLyricsDisplay";
import LyricsDisplay from "@/components/player/LyricsDisplay";
import ProgressBar from "@/components/player/ProgressBar";
import { Button } from "@/components/ui/button";
import { MetadataDialog } from "@/components/upload/MetadataDialog";
import { parseYouTubeTitle } from "@/utils/formatters";
import { useParams } from "react-router-dom";

const SongPlayer: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [song, setSong] = useState<Song | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lyricsLoading, setLyricsLoading] = useState(false);
  const [audioReady, setAudioReady] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [vocalsMuted, setVocalsMuted] = useState(false);
  const [showMetadataDialog, setShowMetadataDialog] = useState(false);
  const [isSearchingLyrics, setIsSearchingLyrics] = useState(false);
  const instrumentalRef = useRef<HTMLAudioElement | null>(null);
  const vocalsRef = useRef<HTMLAudioElement | null>(null);

  // Fetch song on mount
  useEffect(() => {
    if (!id) {
      setError("No song ID provided.");
      setLoading(false);
      return;
    }
    setLoading(true);
    getSongById(id)
      .then((res) => {
        if (res.data) {
          setSong(res.data);
        } else {
          setError("Song not found.");
        }
      })
      .catch(() => setError("Failed to fetch song."))
      .finally(() => setLoading(false));
  }, [id]);

  // Fetch lyrics if missing
  useEffect(() => {
    if (!song || song.lyrics || song.syncedLyrics) return;
    setLyricsLoading(true);
    fetchLyrics(song.title, song.artist, song.album, song.id)
      .then(async (res) => {
        if (res.data && (res.data.lyrics || res.data.syncedLyrics)) {
          const updated = {
            ...song,
            lyrics: res.data.lyrics ?? "",
            syncedLyrics: res.data.syncedLyrics ?? "",
          };
          setSong(updated);
          // Persist lyrics to backend
          await updateSongMetadata(song.id, {
            lyrics: res.data.lyrics ?? "",
            syncedLyrics: res.data.syncedLyrics ?? "",
          });
        }
      })
      .catch(() => {
        /* ignore lyrics fetch errors */
      })
      .finally(() => setLyricsLoading(false));
  }, [song]);

  // Audio event handlers
  useEffect(() => {
    const vocals = vocalsRef.current;
    if (!vocals) return;
    const onEnded = () => setPlaying(false);
    vocals.addEventListener("ended", onEnded);
    return () => {
      vocals.removeEventListener("ended", onEnded);
    };
  }, [vocalsRef, song]);

  // Play/pause sync
  useEffect(() => {
    const instrumental = instrumentalRef.current;
    const vocals = vocalsRef.current;
    if (!instrumental || !vocals) return;
    if (playing) {
      instrumental.play().catch(() => setPlaying(false));
      vocals.play().catch(() => setPlaying(false));
    } else {
      instrumental.pause();
      vocals.pause();
    }
  }, [playing]);

  // Mute vocals (set volume to 0)
  useEffect(() => {
    const vocals = vocalsRef.current;
    if (vocals) vocals.volume = vocalsMuted ? 0 : 1;
  }, [vocalsMuted]);

  // Seek
  const handleSeek = (time: number) => {
    const instrumental = instrumentalRef.current;
    const vocals = vocalsRef.current;
    if (instrumental && vocals) {
      instrumental.currentTime = time;
      vocals.currentTime = time;
      setCurrentTime(time);
    }
  };

  // Show metadata dialog if lyrics are missing
  useEffect(() => {
    if (
      song &&
      !song.lyrics &&
      !song.syncedLyrics &&
      !loading &&
      !lyricsLoading
    ) {
      setShowMetadataDialog(true);
    }
  }, [song, loading, lyricsLoading]);

  // Handler for metadata dialog submit
  const handleMetadataSubmit = async (metadata: {
    artist: string;
    title: string;
    album?: string;
  }) => {
    if (!song) return;
    setIsSearchingLyrics(true);
    try {
      const res = await fetchLyrics(
        metadata.title,
        metadata.artist,
        metadata.album,
        song.id
      );
      if (res.data && (res.data.lyrics || res.data.syncedLyrics)) {
        const updated = {
          ...song,
          lyrics: res.data.lyrics ?? "",
          syncedLyrics: res.data.syncedLyrics ?? "",
        };
        setSong(updated);
        await updateSongMetadata(song.id, {
          lyrics: res.data.lyrics ?? "",
          syncedLyrics: res.data.syncedLyrics ?? "",
        });
        setShowMetadataDialog(false);
      }
    } catch (err) {
      // Optionally handle error
    } finally {
      setIsSearchingLyrics(false);
    }
  };

  // Button handlers
  const handlePlayPause = () => {
    setPlaying((p) => !p);
  };
  const handleMute = () => {
    setVocalsMuted((v) => !v);
  };

  // Only render player if song is loaded
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <div className="text-lg text-orange-peel animate-pulse">
          Loading song...
        </div>
      </div>
    );
  }
  if (error || !song) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <div className="text-lg text-destructive">
          {error || "Song not found."}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full w-full items-center justify-center p-4">
      <MetadataDialog
        isOpen={showMetadataDialog}
        onClose={() => setShowMetadataDialog(false)}
        onSubmit={handleMetadataSubmit}
        initialMetadata={
          song ? parseYouTubeTitle(song.title) : { title: "", artist: "" }
        }
        videoTitle={song?.title ?? ""}
        isSubmitting={isSearchingLyrics}
      />
      <div className="w-full max-w-3xl mx-auto">
        <h1 className="text-3xl font-bold text-center mb-2 text-orange-peel">
          {song.title}
        </h1>
        <h2 className="text-xl text-center mb-4 text-background/80">
          {song.artist}
        </h2>
        <div className="aspect-video w-full bg-black/80 rounded-xl overflow-hidden mb-4 flex items-center justify-center relative">
          {lyricsLoading ? (
            <div className="text-orange-peel animate-pulse text-xl">
              Fetching lyrics...
            </div>
          ) : song.syncedLyrics ? (
            <SyncedLyricsDisplay
              syncedLyrics={song.syncedLyrics}
              currentTime={currentTime * 1000}
              className="h-full"
            />
          ) : (
            <LyricsDisplay
              lyrics={song.lyrics ?? ""}
              progress={duration ? currentTime / duration : 0}
              currentTime={currentTime * 1000}
            />
          )}
        </div>
        <audio
          ref={instrumentalRef}
          src={getAudioUrl(song.id, "instrumental")}
          onCanPlay={() => setAudioReady(true)}
          onLoadedMetadata={(e) => setDuration(e.currentTarget.duration)}
          onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
          onEnded={() => setPlaying(false)}
          onError={() => {
            setAudioReady(false);
            setError("Failed to load instrumental audio.");
          }}
          className="w-full hidden"
        />
        <audio
          ref={vocalsRef}
          src={getAudioUrl(song.id, "vocals")}
          onCanPlay={() => setAudioReady(true)}
          onLoadedMetadata={() => setAudioReady(true)}
          onError={() => {
            setAudioReady(false);
            setError("Failed to load vocal audio.");
          }}
          className="w-full hidden"
        />
        <div className="flex flex-col gap-2 mt-2">
          <ProgressBar
            value={duration ? (currentTime / duration) * 100 : 0}
            max={100}
            onChange={(val) => handleSeek((val / 100) * duration)}
            className="mb-2"
          />
          <div className="flex justify-center items-center gap-6">
            <Button
              className="p-3 rounded-full bg-accent text-background"
              onClick={handleMute}
              aria-label={vocalsMuted ? "Unmute vocals" : "Mute vocals"}
            >
              {vocalsMuted ? <VolumeX size={24} /> : <Volume2 size={24} />}
            </Button>
            <Button
              className="p-4 rounded-full bg-orange-peel text-russet"
              onClick={handlePlayPause}
              aria-label={playing ? "Pause" : "Play"}
              disabled={!audioReady}
            >
              {playing ? (
                <Pause size={32} />
              ) : (
                <Play size={32} style={{ marginLeft: "3px" }} />
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SongPlayer;
