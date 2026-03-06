import React from "react";
import { Button } from "@/components/ui/button";
import { Play, Pause, Maximize } from "lucide-react";
import ProgressBar from "@/features/player/components/subcomponents/ProgressBar";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { sessionWebSocketService } from "@/services/sessionWebSocketService";

const PerformanceTransportBar: React.FC = () => {
  const { isPlaying, currentTime, duration, userPlay, userPause, seek } =
    useKaraokePlayerStore();

  return (
    <div className="border-t border-orange-peel/30 pt-3 flex flex-col gap-2 shrink-0">
      <div className="flex items-center justify-between">
        <Button
          className="rounded-full h-14 w-14 bg-gradient-to-br from-orange-peel to-rust hover:from-orange-peel/90 hover:to-rust/90 shadow-lg transition-all hover:scale-105"
          onClick={isPlaying ? userPause : userPlay}
          aria-label={isPlaying ? "Pause" : "Play"}
        >
          {isPlaying ? <Pause size={28} /> : <Play size={28} />}
        </Button>

        <Button
          variant="ghost"
          size="icon"
          className="h-10 w-10 text-lemon-chiffon/70 hover:text-lemon-chiffon"
          onClick={() => sessionWebSocketService.toggleFullscreen()}
          aria-label="Toggle fullscreen on stage"
        >
          <Maximize size={22} />
        </Button>
      </div>

      <ProgressBar
        currentTime={currentTime}
        duration={duration}
        onSeek={seek}
        className="w-full"
      />
    </div>
  );
};

export default PerformanceTransportBar;
