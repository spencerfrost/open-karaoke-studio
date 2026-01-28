import React, { ReactNode } from "react";
import NavBar from "./NavBar";
import { Music, Upload, List, Sliders } from "lucide-react";
import { useSessionStore } from "@/stores/sessionStore";

interface AppLayoutProps {
  children: ReactNode;
}

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const { isHost, sessionId } = useSessionStore();

  // Filter navigation items based on user's device type
  const getNavigationItems = () => {
    const baseItems = [
      { name: "Library", path: "/", icon: Music },
      { name: "Add", path: "/add", icon: Upload },
    ];

    // Only show navigation items if user is in a session
    if (!sessionId) {
      return baseItems;
    }

    // Host devices see "Stage" tab
    if (isHost) {
      return [...baseItems, { name: "Stage", path: "/stage", icon: List }];
    }

    // Performer devices see "Controls" tab
    return [
      ...baseItems,
      { name: "Controls", path: "/controls", icon: Sliders },
    ];
  };

  return (
    <div className="flex flex-col h-screen">
      <div className="vintage-texture-overlay" />
      <div className="vintage-sunburst-pattern" />
      <main className="flex-1 overflow-auto p-2 sm:p-4 relative z-10">
        {children}
      </main>
      <NavBar items={getNavigationItems()} />
    </div>
  );
};

export default AppLayout;
