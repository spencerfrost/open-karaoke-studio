import React, { ReactNode } from "react";
import NavBar from "./NavBar";
import { Music, Upload, List, Sliders, Mic2, ShieldCheck, Waves } from "lucide-react";
import { useSessionStore } from "@/stores/sessionStore";
import { useAuthStore } from "@/stores/authStore";

interface AppLayoutProps {
  children: ReactNode;
}

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const { isHost, sessionId } = useSessionStore();
  const { user } = useAuthStore();

  // Filter navigation items based on user's device type
  const getNavigationItems = () => {
    const baseItems = [
      { name: "Library", path: "/", icon: Music },
      { name: "Add", path: "/add", icon: Upload },
    ];

    const hostItems = [];
    if (user?.isHost || user?.isAdmin) {
      hostItems.push({ name: "KJ", path: "/host", icon: Mic2 });
    }
    if (user?.isAdmin) {
      hostItems.push({ name: "Admin", path: "/admin", icon: ShieldCheck });
      hostItems.push({
        name: "Compare",
        path: "/admin/compare-three-track",
        icon: Waves,
      });
    }

    // Only show session-specific navigation if user is in a session
    if (!sessionId) {
      return [...baseItems, ...hostItems];
    }

    // Host devices see "Stage" tab
    if (isHost) {
      return [
        ...baseItems,
        { name: "Stage", path: "/stage", icon: List },
        ...hostItems,
      ];
    }

    // Performer devices see "Controls" tab
    return [
      ...baseItems,
      { name: "Controls", path: "/controls", icon: Sliders },
      ...hostItems,
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
