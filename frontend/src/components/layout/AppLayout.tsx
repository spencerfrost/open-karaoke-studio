import React, { ReactNode } from "react";
import NavBar from "./NavBar";
import { Music, Upload, List, Settings, Sliders } from "lucide-react";
import vintageTheme from "../../utils/theme";

interface AppLayoutProps {
  children: ReactNode;
}

const navigationItems = [
  { name: "Library", path: "/", icon: Music },
  { name: "Add", path: "/add", icon: Upload },
  { name: "Stage", path: "/stage", icon: List },
  { name: "Performance", path: "/controls", icon: Sliders },
  { name: "Settings", path: "/settings", icon: Settings },
];

const textureOverlayStyle = vintageTheme.getTextureOverlay();
const sunburstPatternStyle = vintageTheme.getSunburstPattern();

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  return (
    <div className="flex flex-col h-screen">
      <div style={textureOverlayStyle} />
      <div style={sunburstPatternStyle} />
      <main className="flex-1 overflow-auto p-4 relative z-10">{children}</main>
      <NavBar items={navigationItems} />
    </div>
  );
};

export default AppLayout;
