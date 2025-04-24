import React from "react";
import { usePlayer } from "../../context/PlayerContext";
import { useSettings } from "../../context/SettingsContext";
import vintageTheme from "../../utils/theme";

interface LyricsDisplayProps {
  className?: string;
}

const LyricsDisplay: React.FC<LyricsDisplayProps> = ({ className = "" }) => {
  const { state: playerState, getCurrentLyric } = usePlayer();
  const { settings } = useSettings();
  const colors = vintageTheme.colors;

  // Get current and next lyrics
  const { current, next } = getCurrentLyric();

  // Calculate font sizes based on settings
  const getFontSize = () => {
    switch (settings.display.lyricsSize) {
      case "small":
        return { current: "text-3xl", next: "text-xl" };
      case "large":
        return { current: "text-6xl", next: "text-3xl" };
      case "medium":
      default:
        return { current: "text-4xl", next: "text-2xl" };
    }
  };

  const fontSizes = getFontSize();

  // If no current lyrics or song is not playing
  if (!current || playerState.status === "idle" || !playerState.currentSong) {
    return (
      <div
        className={`flex flex-col items-center justify-center text-center p-4 ${className}`}
      >
        <div
          className="text-2xl font-semibold mb-4"
          style={{ color: colors.lemonChiffon }}
        >
          No lyrics available
        </div>
        {playerState.currentSong && (
          <div style={{ color: `${colors.lemonChiffon}80` }}>
            Enjoy the music!
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      className={`flex flex-col items-center justify-center p-6 ${className}`}
    >
      {/* Current singer */}
      {playerState.currentSong && (
        <div
          className="font-mono tracking-wide mb-8"
          style={{ color: colors.orangePeel }}
        >
          SINGER: {playerState.currentSong.singer}
        </div>
      )}

      {/* Current lyric */}
      <div
        className={`${fontSizes.current} font-semibold mb-6 text-center max-w-3xl`}
        style={{
          color: colors.lemonChiffon,
          textShadow: `2px 2px 0 ${colors.darkCyan}80, -2px -2px 0 ${colors.orangePeel}80`,
        }}
      >
        {current.text}
      </div>

      {/* Next lyric */}
      {next && (
        <div
          className={`${fontSizes.next} text-center max-w-3xl`}
          style={{ opacity: 0.6, color: colors.lemonChiffon }}
        >
          {next.text}
        </div>
      )}
    </div>
  );
};

export default LyricsDisplay;
