import React, { useEffect } from "react";
import { useKaraokePlayerStore } from "../stores/useKaraokePlayerStore";
import { Button } from "@/components/ui/button";
import { Volume2, Play, Pause } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import PerformanceControlInput from "@/components/PerformanceControlsInput";
import ProgressBar from "@/components/player/ProgressBar";
import WebSocketStatus from "@/components/WebsocketStatus";

/**
 * Mobile-optimized dedicated page for performance controls
 * Allows performers to control their performance settings from their mobile device
 * Uses global controls for the entire application
 */
const PerformanceControlsPage: React.FC = () => {
  const {
    // WebSocket connection and state
    connect,
    disconnect,
    connected,
    // Performance control state
    vocalVolume,
    instrumentalVolume,
    lyricsSize,
    lyricsOffset,
    // Player state
    isPlaying,
    currentTime,
    duration,
    // Performance control actions
    setVocalVolume,
    setInstrumentalVolume,
    setLyricsSize,
    setLyricsOffset,
    // Player controls
    userPlay,
    userPause,
    seek,
  } = useKaraokePlayerStore();

  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  const toggleVocalsVolume = () => {
    if (vocalVolume > 0) {
      setVocalVolume(0);
    } else {
      setVocalVolume(100);
    }
  };

  const toggleInstrumentalVolume = () => {
    if (instrumentalVolume > 0) {
      setInstrumentalVolume(0);
    } else {
      setInstrumentalVolume(100);
    }
  };

  function getLyricsSizeValue(lyricsSize: string): number {
    if (lyricsSize === "small") return 1;
    if (lyricsSize === "medium") return 2;
    return 3;
  }

  const parseLyricsSize = (value: number) => {
    switch (value) {
      case 1:
        setLyricsSize("small");
        break;
      case 2:
        setLyricsSize("medium");
        break;
      case 3:
        setLyricsSize("large");
        break;
      default:
        setLyricsSize("medium");
    }
  };

  let lyricsSizeLabel = "Medium";
  if (lyricsSize === "small") {
    lyricsSizeLabel = "Small";
  } else if (lyricsSize === "large") {
    lyricsSizeLabel = "Large";
  }

  return (
    <AppLayout>
      <div
        className="h-full flex flex-col"
        style={{ touchAction: "none" }} // Prevent dragging on mobile
      >
        <div className="flex justify-between items-center mb-6 z-10">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-orange-peel font-retro">
              Performance Controls
            </h1>
            <div>
              <pre className="text-xs text-lemon-chiffon bg-black/40 rounded px-2 py-1 max-w-xs overflow-x-auto">
                {isPlaying ? "Playing" : "Paused"}
              </pre>
            </div>
          </div>
          <WebSocketStatus connected={connected} />
        </div>

        {!connected ? (
          <div className="flex-1 flex items-center justify-center flex-col">
            <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-orange-peel mb-4"></div>
            <p className="text-lg text-lemon-chiffon">
              Connecting to performance controls...
            </p>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center flex-col">
            <div className="flex items-center justify-center mb-4 w-full gap-4">
              <Button
                className="rounded-full"
                size="icon"
                onClick={isPlaying ? userPause : userPlay}
                aria-label={isPlaying ? "Pause" : "Play"}
              >
                {isPlaying ? <Pause size={24} /> : <Play size={24} />}
              </Button>
              <ProgressBar
                currentTime={currentTime}
                durationMs={duration}
                onSeek={seek}
                className="w-full"
              />
            </div>
            <div className="flex-1 grid grid-cols-3 gap-4">
              {/* Vocal Volume Section */}
              <PerformanceControlInput
                icon="mic"
                label="Vocals"
                value={vocalVolume}
                valueDisplay={`${Math.round(vocalVolume * 100)}%`}
                min={0}
                max={1}
                step={0.05}
                onValueChange={setVocalVolume}
              >
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={toggleVocalsVolume}
                >
                  <Volume2 size={24} />
                </Button>
              </PerformanceControlInput>

              {/* Music Volume Section */}
              <PerformanceControlInput
                icon="music"
                label="Instrumental"
                value={instrumentalVolume}
                valueDisplay={`${Math.round(instrumentalVolume * 100)}%`}
                min={0}
                max={1}
                step={0.05}
                onValueChange={(value) => setInstrumentalVolume(value)}
              >
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={toggleInstrumentalVolume}
                >
                  <Volume2 size={24} />
                </Button>
              </PerformanceControlInput>

              {/* Lyrics Size Section */}
              <PerformanceControlInput
                icon="maximize-2"
                label="Lyrics Size"
                value={getLyricsSizeValue(lyricsSize)}
                valueDisplay={lyricsSizeLabel}
                min={1}
                max={3}
                step={1}
                onValueChange={parseLyricsSize}
              >
                <Button variant="ghost" size="icon">
                  Aa
                </Button>
              </PerformanceControlInput>
            </div>
            <div>
              <div className="flex items-center justify-center gap-4 mt-4">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setLyricsOffset(lyricsOffset - 200)}
                >
                  <span className="text-4xl">-</span>
                </Button>
                <div>
                  <span className="text-lg text-lemon-chiffon">
                    {lyricsOffset}ms
                  </span>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setLyricsOffset(lyricsOffset + 200)}
                >
                  <span className="text-4xl">+</span>
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
};

export default PerformanceControlsPage;
