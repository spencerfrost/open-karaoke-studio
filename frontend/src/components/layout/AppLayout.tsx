import React, { ReactNode } from "react";
import NavBar from "./NavBar";
import { Music, Upload, List, Sliders } from "lucide-react";

interface AppLayoutProps {
  children: ReactNode;
}

const navigationItems = [
  { name: "Library", path: "/", icon: Music },
  { name: "Add", path: "/add", icon: Upload },
  { name: "Stage", path: "/stage", icon: List },
  { name: "Controls", path: "/controls", icon: Sliders },
];

// OLD APPROACH - using theme.ts functions
// const textureOverlayStyle = vintageTheme.getTextureOverlay();
// const sunburstPatternStyle = vintageTheme.getSunburstPattern();

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  return (
    <div className="flex flex-col h-screen">
      {/* NEW APPROACH - using Tailwind utility classes */}
      <div className="vintage-texture-overlay" />
      <div className="vintage-sunburst-pattern" />
      <main className="flex-1 overflow-auto p-4 relative z-10">{children}</main>
      <NavBar items={navigationItems} />
    </div>
  );
};

export default AppLayout;
