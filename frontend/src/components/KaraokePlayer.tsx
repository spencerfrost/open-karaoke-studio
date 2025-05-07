import { useKaraokeQueueStore } from "@/stores/useKaraokeQueueStore";
import { usePerformanceControlsStore } from "@/stores/usePerformanceControlsStore";
import { VolumeX, Volume2, Pause, Play } from "lucide-react";
import ProgressBar from "./player/ProgressBar";
import { Button } from "./ui/button";

const KaraokePlayer = () => {
  const { play, pause, currentTime, duration, isPlaying, audioError } =
    usePerformanceControlsStore();
  const { currentSong, items } = useKaraokeQueueStore();

  const handlePlayPause = () => {
    if (isPlaying) {
      pause();
    } else {
      play();
    }
  };

  return (
    <div className="flex flex-col gap-4 h-full p-6 relative z-20">
      <h1 className="text-3xl font-bold text-center mb-2 text-orange-peel">
        {currentSong?.song.title}
      </h1>
      <h2 className="text-xl text-center mb-4 text-background/80">
        {currentSong?.song.artist}
      </h2>
      <div className="aspect-video w-full bg-black/80 rounded-xl overflow-hidden flex items-center justify-center relative">
        {lyricsContent}
      </div>
      {/* Bottom controls */}
      <div
        className="p-4 pt-0 bg-gradient-to-b from-black to-transparent"
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
            className="p-3 rounded-full bg-accent text-background"
            onClick={handleMute}
            aria-label={vocalVolume === 0 ? "Unmute vocals" : "Mute vocals"}
          >
            {vocalVolume === 0 ? <VolumeX size={24} /> : <Volume2 size={24} />}
          </Button>

          <Button
            className="p-4 rounded-full bg-orange-peel text-russet"
            onClick={handlePlayPause}
            aria-label={isPlaying ? "Pause" : "Play"}
            disabled={!isReady}
          >
            {isPlaying ? <Pause size={32} /> : <Play size={32} />}
          </Button>
        </div>
      </div>
    </div>
  );
};

export default KaraokePlayer;
