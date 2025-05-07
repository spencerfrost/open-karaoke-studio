import React, { useEffect } from "react";
import { usePerformanceControlsStore } from "../stores/usePerformanceControlsStore";
import { Button } from "@/components/ui/button";
import { Volume2, Music, Mic, Maximize2 } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import PerformanceControlInput from "@/components/PerformanceControlsInput";

/**
 * Mobile-optimized dedicated page for performance controls
 * Allows performers to control their performance settings from their mobile device
 * Uses global controls for the entire application
 */
const PerformanceControlsPage: React.FC = () => {
  const {
    connect,
    disconnect,
    connected,
    vocalVolume,
    instrumentalVolume,
    lyricsSize,
    setVocalVolume,
    setInstrumentalVolume,
    setLyricsSize,
  } = usePerformanceControlsStore();

  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  const toggleVocals = () => {
    if (vocalVolume > 0) {
      setVocalVolume(0);
    } else {
      setVocalVolume(100);
    }
  };

  // Add this helper function above the component
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

  // Extracted label for lyrics size
  let lyricsSizeLabel = "Medium";
  if (lyricsSize === "small") {
    lyricsSizeLabel = "Small";
  } else if (lyricsSize === "large") {
    lyricsSizeLabel = "Large";
  }

  return (
    <AppLayout>
      <div className="h-full flex flex-col">
        <div className="flex justify-between items-center mb-6 z-10">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-orange-peel font-retro">
              Performance Controls
            </h1>
          </div>
          {connected ? (
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-dark-cyan animate-pulse"></span>
              <span className="text-sm text-dark-cyan">Live</span>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-rust animate-pulse"></span>
              <span className="text-sm text-rust">Connecting...</span>
            </div>
          )}
        </div>

        {!connected ? (
          <div className="flex-1 flex items-center justify-center flex-col">
            <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-orange-peel mb-4"></div>
            <p className="text-lg text-lemon-chiffon">
              Connecting to performance controls...
            </p>
          </div>
        ) : (
          <div className="flex-1 grid grid-cols-3 gap-4">
            {/* Vocal Volume Section */}
            <PerformanceControlInput
              icon="mic"
              label="Vocals"
              value={vocalVolume}
              valueDisplay={`${vocalVolume}%`}
              min={0}
              max={100}
              step={5}
              onValueChange={setVocalVolume}
            >
              <Button variant="ghost" size="icon" onClick={toggleVocals}>
                <Volume2 size={24} />
              </Button>
            </PerformanceControlInput>

            {/* Music Volume Section */}
            <PerformanceControlInput
              icon="music"
              label="Instrumental"
              value={instrumentalVolume}
              valueDisplay={`${instrumentalVolume}%`}
              min={0}
              max={100}
              step={5}
              onValueChange={setInstrumentalVolume}
            >
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setInstrumentalVolume(0)}
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
        )}
      </div>
    </AppLayout>
  );
};

export default PerformanceControlsPage;
