import React, { ReactNode, useState } from "react";
import { ChevronRight, ChevronDown, List, Music, Settings, Upload } from "lucide-react";
import { usePlayer } from "../../context/PlayerContext";
import vintageTheme from "../../utils/theme";
import NavBar from "./NavBar";

interface PlayerLayoutProps {
  children: ReactNode;
  showControls?: boolean;
}

const navigationItems = [
  { name: "Library", path: "/", icon: Music },
  { name: "Add", path: "/add", icon: Upload },
  { name: "Queue", path: "/queue", icon: List },
  { name: "Settings", path: "/settings", icon: Settings },
];

const PlayerLayout: React.FC<PlayerLayoutProps> = ({
  children,
  showControls = true,
}) => {
  const { state: playerState } = usePlayer();
  const [showMenu, setShowMenu] = useState(false);

  return (
    <div
      style={{ background: vintageTheme.background }}
      className="w-screen h-screen overflow-hidden relative"
    >
      <div style={vintageTheme.getTextureOverlay()} />
      <div style={vintageTheme.getSunburstPattern()} />

      {showControls && playerState.currentSong && (
        <div
          className="absolute top-0 left-0 right-0 p-4 flex justify-between items-center z-20"
          style={{
            backgroundImage:
              "linear-gradient(to bottom, rgba(0,0,0,0.7), transparent)",
          }}
        >
          <div className="flex items-center">
            {/* Song info */}
            <div>
              <h2 className="font-semibold">
                {playerState.currentSong.song.title}
              </h2>
              <p className="text-sm text-background">
                {playerState.currentSong.song.artist}
              </p>
            </div>
          </div>

          {/* Menu toggle button */}
          <button
            className="p-2 rounded-lg bg-accent text-foreground"
            onClick={() => setShowMenu(!showMenu)}
          >
            {showMenu ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
          </button>
        </div>
      )}

      {/* Main content area */}
      <div className="relative z-10 h-full">{children}</div>
      <NavBar items={navigationItems} />
    </div>
  );
};

export default PlayerLayout;
