import React, { ReactNode } from "react";
import { List, Music, Settings, Upload } from "lucide-react";
import vintageTheme from "../../utils/theme";
import NavBar from "./NavBar";

interface PlayerLayoutProps {
  children: ReactNode;
}

const navigationItems = [
  { name: "Library", path: "/", icon: Music },
  { name: "Add", path: "/add", icon: Upload },
  { name: "Queue", path: "/queue", icon: List },
  { name: "Settings", path: "/settings", icon: Settings },
];

const PlayerLayout: React.FC<PlayerLayoutProps> = ({ children }) => {
  return (
    <div
      style={{ background: vintageTheme.background }}
      className="w-screen min-h-screen overflow-scroll relative"
    >
      <div style={vintageTheme.getTextureOverlay()} />
      <div style={vintageTheme.getSunburstPattern()} />

      {/* Main content area */}
      <div className="relative z-10 h-full container mx-auto">{children}</div>
      <NavBar items={navigationItems} />
    </div>
  );
};

export default PlayerLayout;
