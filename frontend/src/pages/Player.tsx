import React, { useEffect, useState, useRef } from "react";
import { useParams } from "react-router-dom";
import { Play, Pause, SkipForward, Volume2, VolumeX } from "lucide-react";
import { usePlayer } from "../context/PlayerContext";
import { useQueue } from "../context/QueueContext";
import PlayerLayout from "../components/layout/PlayerLayout";
import LyricsDisplay from "../components/player/LyricsDisplay";
import AudioVisualizer from "../components/player/AudioVisualizer";
import ProgressBar from "../components/player/ProgressBar";
import QueueList from "../components/queue/QueueList";
import { skipToNext } from "../services/queueService";
import { useSettings } from "../context/SettingsContext";
import { getAudioUrl, getSongById, searchLyrics } from "../services/songService";
import { Song } from "../types/Song";
import { MetadataDialog } from "../components/upload/MetadataDialog";
import { parseYouTubeTitle } from "../utils/formatters";

const PlayerPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { state: playerState, dispatch: playerDispatch } = usePlayer();
  const { state: queueState, dispatch: queueDispatch } = useQueue();
  const { settings } = useSettings();
  const [vocalsMuted, setVocalsMuted] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [progress, setProgress] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [currentSong, setCurrentSong] = useState<Song | null>(null);
  const [showMetadataDialog, setShowMetadataDialog] = useState(false);
  const [isSearchingLyrics, setIsSearchingLyrics] = useState(false);
  const [noLyricsDetected, setNoLyricsDetected] = useState(false);
  
  // Derived metadata from the song title or ID
  const derivedMetadata = currentSong?.title
    ? parseYouTubeTitle(currentSong.title)
    : { title: "", artist: "Unknown Artist" };

  useEffect(() => {
    if (id) {
      const queueItem =
        queueState.items.find((item) => item.song.id === id) ||
        (queueState.currentItem?.song.id === id
          ? queueState.currentItem
          : null);

      if (queueItem) {
        playerDispatch({ type: "SET_CURRENT_SONG", payload: queueItem });
        playerDispatch({
          type: "SET_DURATION",
          payload: queueItem.song.duration,
        });
        queueDispatch({ type: "SET_CURRENT_ITEM", payload: queueItem });

        setCurrentSong(queueItem.song);
      } else {
        fetchSongDetails(id);
      }

      setTimeout(() => {
        playerDispatch({ type: "SET_STATUS", payload: "playing" });
      }, 500);
    }
  }, [
    id,
    playerDispatch,
    queueDispatch,
    queueState.items,
    queueState.currentItem,
  ]);

  // Fetch song details if needed
  const fetchSongDetails = async (songId: string) => {
    try {
      const response = await getSongById(songId);
      if (response.data) {
        setCurrentSong(response.data);
      }
    } catch (error) {
      console.error("Failed to fetch song details:", error);
    }
  };

  // Check if lyrics are available and show dialog if needed
  useEffect(() => {
    if (currentSong && !noLyricsDetected) {
      const hasLyrics = 
        currentSong.lyrics?.trim() ?? 
        currentSong.syncedLyrics?.trim() ?? 
        "";
      
      if (!hasLyrics) {
        setNoLyricsDetected(true);
        setShowMetadataDialog(true);
      }
    }
  }, [currentSong, noLyricsDetected]);

  useEffect(() => {
    const audioElement = audioRef.current;
    if (!audioElement) return;

    const handleTimeUpdate = () => {
      const currentTimeValue = audioElement.currentTime;
      const duration = audioElement.duration;
      if (duration > 0) {
        const calculatedProgress = currentTimeValue / duration;
        console.log("Audio Progress:", calculatedProgress);
        setProgress(calculatedProgress);
        // Convert current time to milliseconds for synced lyrics
        setCurrentTime(currentTimeValue * 1000);
      }
    };

    audioElement.addEventListener("timeupdate", handleTimeUpdate);

    return () => {
      audioElement.removeEventListener("timeupdate", handleTimeUpdate);
    };
  }, [audioRef]);

  const handlePlayPause = () => {
    playerDispatch({ type: "TOGGLE_PLAY_PAUSE" });
  };

  const handleSkipNext = async () => {
    try {
      const response = await skipToNext();

      if (response.data) {
        queueDispatch({ type: "SET_CURRENT_ITEM", payload: response.data });

        if (response.data) {
          playerDispatch({ type: "SET_CURRENT_SONG", payload: response.data });
          playerDispatch({
            type: "SET_DURATION",
            payload: response.data.song.duration,
          });
          playerDispatch({ type: "SET_STATUS", payload: "playing" });
        } else {
          playerDispatch({ type: "SET_CURRENT_SONG", payload: null });
          playerDispatch({ type: "SET_STATUS", payload: "idle" });
        }
      }
    } catch (err) {
      console.error("Failed to skip to next song:", err);
    }
  };

  // Handle lyrics search submission
  const handleMetadataSubmit = async (metadata: { artist: string; title: string }) => {
    if (!id) return;
    
    setIsSearchingLyrics(true);
    
    try {
      // Search for lyrics based on metadata
      const response = await searchLyrics({
        track_name: metadata.title,
        artist_name: metadata.artist,
      });
      
      if (response.data && response.data.length > 0) {
        // Get first result
        const lyricsData = response.data[0];
        
        // Update the current song object with the new lyrics
        if (currentSong && (lyricsData.plainLyrics || lyricsData.syncedLyrics)) {
          setCurrentSong({
            ...currentSong,
            lyrics: lyricsData.plainLyrics ?? "",
            syncedLyrics: lyricsData.syncedLyrics ?? "",
          });
        }
      }
    } catch (error) {
      console.error("Failed to search for lyrics:", error);
    } finally {
      setIsSearchingLyrics(false);
      setShowMetadataDialog(false);
    }
  };

  // Toggle vocals
  const handleToggleVocals = () => {
    if (vocalsMuted) {
      // Restore vocal volume
      playerDispatch({
        type: "SET_VOCAL_VOLUME",
        payload: settings.audio.defaultVocalVolume,
      });
      setVocalsMuted(false);
    } else {
      // Mute vocals
      playerDispatch({ type: "SET_VOCAL_VOLUME", payload: 0 });
      setVocalsMuted(true);
    }
  };

  // Handle seeking (in a real app, this would control the audio element)
  const handleSeek = (time: number) => {
    // For now, just update the current time
    playerDispatch({ type: "SET_CURRENT_TIME", payload: time });
  };

  return (
    <PlayerLayout>
      {/* Metadata Dialog for Lyrics Search */}
      <MetadataDialog
        isOpen={showMetadataDialog}
        onClose={() => setShowMetadataDialog(false)}
        onSubmit={handleMetadataSubmit}
        initialMetadata={derivedMetadata}
        videoTitle={currentSong?.title ?? ""}
        isSubmitting={isSearchingLyrics}
      />

      {playerState.status === "idle" || !playerState.currentSong ? (
        <div className="flex flex-col gap-4 h-full p-6 relative z-20">
          <div className="text-center mt-8">
            <h1 className="text-4xl font-mono tracking-wide mb-2 text-background">
              OPEN KARAOKE STUDIO
            </h1>
            <p className="text-lg opacity-80 text-background">
              Scan the QR code to add songs to the queue
            </p>
          </div>

          {/* Audio test player */}
          {id && (
            <div className="mt-6">
              <div className="aspect-video w-full bg-black/80 overflow-hidden relative">
                <LyricsDisplay
                  songId={id}
                  song={currentSong}
                  progress={progress}
                  currentTime={currentTime}
                />
                <AudioVisualizer 
                  className="absolute bottom-0 left-0 right-0" 
                  expanded={!noLyricsDetected}
                  onExpandedChange={(expanded) => {
                    if (!expanded && noLyricsDetected) {
                      setShowMetadataDialog(true);
                    }
                  }}
                />
              </div>
              <audio
                controls
                autoPlay
                src={getAudioUrl(id, "instrumental")}
                className="w-full"
                ref={audioRef}
              >
                <track kind="captions" src="" label="No captions available" />
              </audio>
            </div>
          )}

          <h2 className="text-2xl font-semibold text-center mb-4 text-orange-peel">
            Up Next
          </h2>

          <div className="max-w-2xl mx-auto w-full rounded-xl overflow-hidden text-background border border-orange-peel">
            <QueueList
              items={queueState.items}
              emptyMessage="No songs in the queue"
            />
          </div>
        </div>
      ) : (
        <div className="flex flex-col h-full relative z-20">
          <div className="flex-1 flex flex-col items-center justify-center">
            <LyricsDisplay
              songId={playerState.currentSong?.song.id || ""}
              song={currentSong || playerState.currentSong?.song}
              progress={progress}
              currentTime={currentTime}
            />
          </div>

          {/* Bottom controls */}
          <div
            className="p-4 bg-gradient-to-t from-black to-transparent"
            style={{ zIndex: 30 }}
          >
            {/* Progress bar */}
            {settings.display.showProgress && (
              <ProgressBar onChange={handleSeek} className="mb-4" />
            )}

            {/* Playback controls */}
            <div className="flex justify-center items-center gap-4">
              <button
                className="p-3 rounded-full bg-accent text-background"
                onClick={handleToggleVocals}
                aria-label={vocalsMuted ? "Unmute vocals" : "Mute vocals"}
              >
                {vocalsMuted ? <VolumeX size={24} /> : <Volume2 size={24} />}
              </button>

              <button
                className="p-4 rounded-full bg-orange-peel text-russet"
                onClick={handlePlayPause}
                aria-label={playerState.status === "playing" ? "Pause" : "Play"}
              >
                {playerState.status === "playing" ? (
                  <Pause size={32} />
                ) : (
                  <Play size={32} style={{ marginLeft: "3px" }} />
                )}
              </button>

              <button
                className="p-3 rounded-full bg-accent text-background"
                onClick={handleSkipNext}
                aria-label="Skip to next song"
              >
                <SkipForward size={24} />
              </button>
            </div>
          </div>
        </div>
      )}
    </PlayerLayout>
  );
};

export default PlayerPage;
