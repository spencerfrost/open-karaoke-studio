import React, { useEffect, useState } from "react";
import { useKaraokePlayerStore } from "../stores/useKaraokePlayerStore";
import { useSessionStore } from "../stores/sessionStore";
import { Button } from "@/components/ui/button";
import { Volume2, Play, Pause, RotateCcw, Minus, Plus } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import PerformanceControlInput from "@/components/PerformanceControlsInput";
import ProgressBar from "@/components/karaoke-player/subcomponents/ProgressBar";
import WebSocketStatus from "@/components/WebsocketStatus";
import KnobControl from "@/components/KnobControl";

/**
 * Mobile-optimized dedicated page for performance controls
 * Allows performers to control their performance settings from their mobile device
 * Uses session-based controls for proper isolation between karaoke sessions
 */
const PerformanceControlsPage: React.FC = () => {
  const [sessionCode, setSessionCode] = useState("");
  const [deviceType, setDeviceType] = useState<"performer" | "controller">("performer");

  // Session state
  const { 
    sessionId, 
    displayCode, 
    isHost, 
    isConnected: sessionConnected, 
    connectionError,
    joinSession,
    createSession
  } = useSessionStore();

  // Player state
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
    // Only connect to performance controls if we have a session
    if (sessionId && sessionConnected) {
      connect();
      return () => {
        disconnect();
      };
    }
  }, [connect, disconnect, sessionId, sessionConnected]);

  const handleJoinSession = async () => {
    if (!sessionCode.trim()) return;
    await joinSession(sessionCode.trim().toUpperCase(), deviceType);
  };

  const handleCreateSession = async () => {
    await createSession(deviceType);
  };

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
            {sessionId && displayCode && (
              <div className="text-sm text-lemon-chiffon bg-black/40 rounded px-2 py-1">
                Session: {displayCode} {isHost ? "(Host)" : ""}
              </div>
            )}
            <div>
              <pre className="text-xs text-lemon-chiffon bg-black/40 rounded px-2 py-1 max-w-xs overflow-x-auto">
                {isPlaying ? "Playing" : "Paused"}
              </pre>
            </div>
          </div>
          <WebSocketStatus connected={connected} />
        </div>

        {/* Session Join UI - shown when not in a session */}
        {!sessionId ? (
          <div className="flex-1 flex items-center justify-center flex-col space-y-8">
            <div className="text-center">
              <h2 className="text-3xl font-bold text-orange-peel mb-4">
                Join a Karaoke Session
              </h2>
              <p className="text-lemon-chiffon/80 mb-8">
                Enter the 4-character session code to control the karaoke performance
              </p>
            </div>

            <div className="w-full max-w-md space-y-6">
              {/* Session Code Input */}
              <div className="space-y-2">
                <label className="block text-sm font-medium text-lemon-chiffon">
                  Session Code
                </label>
                <input
                  type="text"
                  value={sessionCode}
                  onChange={(e) => setSessionCode(e.target.value.toUpperCase())}
                  placeholder="ABCD"
                  maxLength={4}
                  className="w-full text-center text-4xl font-bold tracking-widest bg-gray-800 border-2 border-orange-peel/50 rounded-lg px-4 py-6 focus:outline-none focus:border-orange-peel focus:ring-2 focus:ring-orange-peel/20 uppercase"
                  autoFocus
                />
              </div>

              {/* Device Type Selection */}
              <div className="space-y-2">
                <label className="block text-sm font-medium text-lemon-chiffon">
                  Device Type
                </label>
                <select
                  value={deviceType}
                  onChange={(e) => setDeviceType(e.target.value as "performer" | "controller")}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-peel"
                >
                  <option value="performer">Performer</option>
                  <option value="controller">Controller</option>
                </select>
              </div>

              {/* Join Button */}
              <Button
                onClick={handleJoinSession}
                disabled={!sessionCode.trim() || sessionCode.length !== 4}
                className="w-full bg-orange-peel hover:bg-orange-peel/80 text-black font-bold py-4 text-lg"
              >
                Join Session
              </Button>

              {/* Create Session Option */}
              <div className="text-center">
                <p className="text-lemon-chiffon/60 mb-2">or</p>
                <Button
                  onClick={handleCreateSession}
                  variant="outline"
                  className="border-orange-peel/50 text-orange-peel hover:bg-orange-peel/10"
                >
                  Create New Session
                </Button>
              </div>

              {/* Error Display */}
              {connectionError && (
                <div className="p-4 bg-red-900/50 border border-red-700 rounded-md">
                  <p className="text-red-200 text-center">{connectionError}</p>
                </div>
              )}
            </div>
          </div>
        ) : !connected ? (
          <div className="flex-1 flex items-center justify-center flex-col">
            <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-orange-peel mb-4"></div>
            <p className="text-lg text-lemon-chiffon">
              Connecting to performance controls...
            </p>
          </div>
        ) : (
          /* Performance Controls - shown when in session and connected */
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
                duration={duration}
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
            
            {/* Lyrics Offset Controls */}
            <div className="mt-6 space-y-4">
              <h3 className="text-lg font-semibold text-lemon-chiffon text-center">
                Lyrics Timing
              </h3>
              
              {/* Knob Control for Lyrics Offset */}
              <div className="flex justify-center">
                <KnobControl
                  value={lyricsOffset}
                  onChange={setLyricsOffset}
                  min={-5000}
                  max={5000}
                  step={25}
                  sensitivity={1.5}
                  label="Offset"
                  unit="ms"
                  onReset={() => setLyricsOffset(0)}
                />
              </div>
              
              {/* Quick Adjustment Buttons */}
              <div className="flex items-center justify-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setLyricsOffset(lyricsOffset - 200)}
                  className="flex items-center gap-1"
                >
                  <Minus size={16} />
                  200ms
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setLyricsOffset(lyricsOffset - 50)}
                  className="flex items-center gap-1"
                >
                  <Minus size={16} />
                  50ms
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setLyricsOffset(0)}
                  className="flex items-center gap-1 bg-orange-peel/20 hover:bg-orange-peel/30"
                >
                  <RotateCcw size={16} />
                  Reset
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setLyricsOffset(lyricsOffset + 50)}
                  className="flex items-center gap-1"
                >
                  <Plus size={16} />
                  50ms
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setLyricsOffset(lyricsOffset + 200)}
                  className="flex items-center gap-1"
                >
                  <Plus size={16} />
                  200ms
                </Button>
              </div>
              
              {/* Help Text */}
              <p className="text-xs text-lemon-chiffon/60 text-center">
                {lyricsOffset === 0 ? "Lyrics are synced" : 
                 lyricsOffset > 0 ? "Lyrics appear earlier" : 
                 "Lyrics appear later"}
              </p>
            </div>

            {/* Session Join/Create UI */}
            <div className="mt-8 w-full max-w-md mx-auto">
              <h2 className="text-xl font-semibold text-lemon-chiffon text-center mb-4">
                {sessionId ? "Session Controls" : "Join or Create a Session"}
              </h2>
              {!sessionId ? (
                <>
                  <div className="flex gap-2 mb-4">
                    <input
                      type="text"
                      value={sessionCode}
                      onChange={(e) => setSessionCode(e.target.value)}
                      placeholder="Enter Session Code"
                      className="flex-1 px-4 py-2 text-lg rounded-l-md bg-black border border-orange-peel focus:ring-2 focus:ring-orange-peel focus:outline-none"
                    />
                    <Button
                      onClick={handleJoinSession}
                      className="rounded-r-md"
                      size="lg"
                    >
                      Join
                    </Button>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      onClick={handleCreateSession}
                      className="flex-1"
                      size="lg"
                    >
                      Create Session
                    </Button>
                  </div>
                  <p className="text-xs text-lemon-chiffon/60 text-center mt-2">
                    Enter the session code provided by the host to join an existing performance, or create a new session if you are the host.
                  </p>
                </>
              ) : (
                <div className="text-center">
                  <p className="text-lg text-lemon-chiffon mb-2">
                    Session Code:{" "}
                    <span className="font-bold">{sessionId}</span>
                  </p>
                  <p className="text-xs text-lemon-chiffon/60 mb-4">
                    Share this code with others to join your session.
                  </p>
                  <Button
                    onClick={() => navigator.clipboard.writeText(sessionId)}
                    className="mb-2"
                    size="sm"
                  >
                    Copy Session Code
                  </Button>
                  <Button
                    onClick={disconnect}
                    variant="outline"
                    size="sm"
                  >
                    Leave Session
                  </Button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
};

export default PerformanceControlsPage;
