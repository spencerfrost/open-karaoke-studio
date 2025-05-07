import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Play, Pause, Volume2, VolumeX, Sliders } from "lucide-react";
import PlayerLayout from "../components/layout/PlayerLayout";
import LyricsDisplay from "../components/player/LyricsDisplay";
import ProgressBar from "../components/player/ProgressBar";
import SyncedLyricsDisplay from "@/components/player/SyncedLyricsDisplay";
import { Button } from "@/components/ui/button";
import { useWebAudioKaraokeStore } from "@/stores/useWebAudioKaraokeStore";
import KaraokeQueueList from "../components/queue/KaraokeQueueList";
import { useKaraokeQueueStore } from "@/stores/useKaraokeQueueStore";

const Stage: React.FC = () => {
  const navigate = useNavigate();
  const {
    currentTime,
    duration,
    // isReady,
    isPlaying,
    play,
    seek,
    pause,
    setVocalVol,
    error: audioError,
  } = useWebAudioKaraokeStore();

  const { currentSong, items } = useKaraokeQueueStore();

  const [vocalsMuted, setVocalsMuted] = useState(false);

  const handlePlayPause = () => {
    if (isPlaying) {
      pause();
    } else {
      play();
    }
  };

  const handleToggleVocals = () => {
    if (vocalsMuted) {
      setVocalVol(1);
      setVocalsMuted(false);
    } else {
      setVocalVol(0);
      setVocalsMuted(true);
    }
  };

  if (audioError) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <div className="text-lg text-destructive">
          Audio error: {audioError}
        </div>
      </div>
    );
  }

  // if (!isReady) {
  //   return (
  //     <div className="flex flex-col items-center justify-center h-full">
  //       <div className="text-lg text-orange-peel animate-pulse">Loading...</div>
  //     </div>
  //   );
  // }

  return (
    <PlayerLayout>
      <div className="flex flex-col gap-4 h-full p-6 relative z-20">
        <div className="text-center mt-8">
          <h1 className="text-4xl font-mono tracking-wide mb-2 text-background">
            OPEN KARAOKE STUDIO
          </h1>
          <p className="text-lg opacity-80 text-background">
            Scan the QR code to add songs to the queue
          </p>
        </div>

        <h2 className="text-2xl font-semibold text-center mb-4 text-orange-peel">
          Up Next
        </h2>

        <div className="max-w-2xl mx-auto w-full rounded-xl overflow-hidden text-background border border-orange-peel">
          <KaraokeQueueList
            items={items}
            emptyMessage="No songs in the queue"
          />
        </div>
      </div>
      <div className="flex flex-col h-full relative z-20">
        <div className="flex-1 flex flex-col items-center justify-center">
          {currentSong &&
            (currentSong.song.syncedLyrics ? (
              <SyncedLyricsDisplay
                syncedLyrics={currentSong.song.syncedLyrics}
                currentTime={currentTime * 1000}
                className="h-full"
              />
            ) : (
              <LyricsDisplay
                lyrics={currentSong.song.lyrics || ""}
                progress={duration ? currentTime / duration : 0}
                currentTime={currentTime * 1000}
              />
            ))}
        </div>

        {/* Bottom controls */}
        <div
          className="p-4 bg-gradient-to-t from-black to-transparent"
          style={{ zIndex: 30 }}
        >
          {/* Progress bar */}
          <ProgressBar
            currentTime={currentTime}
            duration={duration}
            onSeek={(val) => seek(val)}
            className="mb-4"
          />

          {/* Playback controls */}
          <div className="flex justify-center items-center gap-4">
            <Button
              className="rounded-full bg-accent text-background"
              onClick={handleToggleVocals}
              aria-label={vocalsMuted ? "Unmute vocals" : "Mute vocals"}
            >
              {vocalsMuted ? <VolumeX size={24} /> : <Volume2 size={24} />}
            </Button>

            <Button
              className="p-4 rounded-full bg-orange-peel text-russet"
              onClick={handlePlayPause}
              aria-label={isPlaying ? "Pause" : "Play"}
            >
              {isPlaying ? <Pause size={32} /> : <Play size={32} />}
            </Button>

            <Button
              className="rounded-full bg-accent text-background z-100"
              onClick={() => navigate("/controls")}
              aria-label="Open performance controls"
            >
              <Sliders size={24} />
            </Button>
          </div>
        </div>
      </div>
    </PlayerLayout>
  );
};

export default Stage;
