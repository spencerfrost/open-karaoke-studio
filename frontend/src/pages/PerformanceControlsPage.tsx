import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { usePerformanceControlsStore } from "../stores/usePerformanceControlsStore";
import { Slider } from "@/components/ui/slider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Volume2,
  VolumeX,
  Music,
  Mic,
  Maximize2,
  Minimize2,
  ArrowLeft,
} from "lucide-react";

/**
 * Mobile-optimized dedicated page for performance controls
 * Allows performers to control their performance settings from their mobile device
 * Uses global controls for the entire application
 */
const PerformanceControlsPage: React.FC = () => {
  const navigate = useNavigate();

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

  const handleBackToPlayer = () => {
    navigate("/player");
  };

  return (
    <div className="min-h-screen p-4 flex flex-col bg-background">
      <div className="texture-overlay" />

      <div className="flex justify-between items-center mb-6 z-10">
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={handleBackToPlayer}
            className="mr-2 text-orange-peel"
          >
            <ArrowLeft size={20} />
          </Button>
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
        <div className="flex-1 flex flex-col gap-6 z-10">
          {/* Vocal Volume Section */}
          <Card className="border border-orange-peel bg-card/80">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Mic size={20} className="text-orange-peel" />
                <span>Vocals</span>
                <span className="ml-auto text-sm bg-orange-peel/20 px-2 py-1 rounded text-orange-peel">
                  {vocalVolume}%
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4">
                <Button
                  variant="ghost"
                  size="icon"
                  className="rounded-full"
                  onClick={() => setVocalVolume(0)}
                >
                  <VolumeX size={24} />
                </Button>

                <Slider
                  value={[vocalVolume]}
                  min={0}
                  max={100}
                  step={5}
                  onValueChange={(values) => setVocalVolume(values[0])}
                  className="flex-1"
                />

                <Button
                  variant="ghost"
                  size="icon"
                  className="rounded-full"
                  onClick={() => setVocalVolume(100)}
                >
                  <Volume2 size={24} />
                </Button>
              </div>

              {/* Quick presets */}
              <div className="flex justify-between gap-2 mt-4">
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1"
                  onClick={() => setVocalVolume(0)}
                >
                  Mute
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1"
                  onClick={() => setVocalVolume(25)}
                >
                  Low
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1"
                  onClick={() => setVocalVolume(50)}
                >
                  Medium
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1"
                  onClick={() => setVocalVolume(100)}
                >
                  Full
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Music Volume Section */}
          <Card className="border border-dark-cyan bg-card/80">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Music size={20} className="text-dark-cyan" />
                <span>Music</span>
                <span className="ml-auto text-sm bg-dark-cyan/20 px-2 py-1 rounded text-dark-cyan">
                  {instrumentalVolume}%
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4">
                <Button
                  variant="ghost"
                  size="icon"
                  className="rounded-full"
                  onClick={() => setInstrumentalVolume(0)}
                >
                  <VolumeX size={24} />
                </Button>

                <Slider
                  value={[instrumentalVolume]}
                  min={0}
                  max={100}
                  step={5}
                  onValueChange={(values) => setInstrumentalVolume(values[0])}
                  className="flex-1"
                />

                <Button
                  variant="ghost"
                  size="icon"
                  className="rounded-full"
                  onClick={() => setInstrumentalVolume(100)}
                >
                  <Volume2 size={24} />
                </Button>
              </div>

              {/* Quick presets */}
              <div className="flex justify-between gap-2 mt-4">
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1"
                  onClick={() => setInstrumentalVolume(0)}
                >
                  Mute
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1"
                  onClick={() => setInstrumentalVolume(25)}
                >
                  Low
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1"
                  onClick={() => setInstrumentalVolume(50)}
                >
                  Medium
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1"
                  onClick={() => setInstrumentalVolume(100)}
                >
                  Full
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Lyrics Size Section */}
          <Card className="border border-orange-peel bg-card/80">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span>Lyrics Size</span>
                <span className="ml-auto text-sm bg-orange-peel/20 px-2 py-1 rounded text-orange-peel capitalize">
                  {lyricsSize}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4">
                <Button
                  variant={lyricsSize === "small" ? "default" : "outline"}
                  className="flex flex-col items-center p-4"
                  onClick={() => setLyricsSize("small")}
                >
                  <Minimize2 size={24} />
                  <span className="mt-2 text-sm">Small</span>
                </Button>

                <Button
                  variant={lyricsSize === "medium" ? "default" : "outline"}
                  className="flex flex-col items-center p-4"
                  onClick={() => setLyricsSize("medium")}
                >
                  <span className="text-xl font-bold">A</span>
                  <span className="mt-2 text-sm">Medium</span>
                </Button>

                <Button
                  variant={lyricsSize === "large" ? "default" : "outline"}
                  className="flex flex-col items-center p-4"
                  onClick={() => setLyricsSize("large")}
                >
                  <Maximize2 size={24} />
                  <span className="mt-2 text-sm">Large</span>
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Common presets section */}
          <Card className="border border-orange-peel bg-card/80">
            <CardHeader>
              <CardTitle>Quick Presets</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <Button
                className="bg-orange-peel text-russet hover:bg-orange-peel/80"
                onClick={() => {
                  setVocalVolume(0);
                  setInstrumentalVolume(100);
                }}
              >
                Karaoke Mode (No Vocals)
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setVocalVolume(30);
                  setInstrumentalVolume(100);
                }}
              >
                Guide Mode (Low Vocals)
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setVocalVolume(100);
                  setInstrumentalVolume(100);
                }}
              >
                Reset Volumes
              </Button>
            </CardContent>
          </Card>
        </div>
      )}

      <div className="text-center text-xs mt-6 opacity-70 z-10">
        <p>Open Karaoke Studio</p>
      </div>
    </div>
  );
};

export default PerformanceControlsPage;
