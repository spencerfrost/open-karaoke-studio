import React, { ReactNode } from "react";
import NavBar from "./NavBar";
import {
  Music,
  Upload,
  List,
  Sliders,
  ShieldCheck,
  Waves,
  Settings,
} from "lucide-react";
import { useSessionStore } from "@/stores/sessionStore";
import { useAuthStore } from "@/stores/authStore";

interface AppLayoutProps {
  children: ReactNode;
  /**
   * Padding for the content area. Pages that are edge-to-edge (the stage)
   * pass "" so nothing frames them with page background.
   */
  contentClassName?: string;
}

const AppLayout: React.FC<AppLayoutProps> = ({
  children,
  contentClassName = "p-2 sm:p-4",
}) => {
  const { isStageDevice, sessionId } = useSessionStore();
  const { user } = useAuthStore();

  // Filter navigation items based on user's device type
  const getNavigationItems = () => {
    const baseItems = [
      { name: "Library", path: "/", icon: Music },
      { name: "Add", path: "/add", icon: Upload },
    ];

    // Settings is where the account lives - logging in as a host, and logging
    // out - so it has to be reachable from the nav, not just by URL.
    const hostItems = [{ name: "Settings", path: "/settings", icon: Settings }];
    if (user?.isAdmin) {
      hostItems.push({ name: "Admin", path: "/admin", icon: ShieldCheck });
      hostItems.push({
        name: "Compare",
        path: "/admin/compare-three-track",
        icon: Waves,
      });
    }

    // No session yet. A host still needs a way in: entering stage mode is the
    // only thing that starts a session, so gating this tab on a session
    // existing would leave the URL bar as the sole entry point.
    if (!sessionId) {
      const canHost = user?.isHost || user?.isAdmin;
      return canHost
        ? [
            ...baseItems,
            { name: "Stage", path: "/stage", icon: List },
            ...hostItems,
          ]
        : [...baseItems, ...hostItems];
    }

    // Host devices see "Stage" tab. A live session makes it the way back into
    // stage mode, so it is highlighted - being out here is the temporary state.
    if (isStageDevice) {
      return [
        ...baseItems,
        { name: "Stage", path: "/stage", icon: List, highlight: true },
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
      <main
        className={`flex-1 overflow-auto relative z-10 ${contentClassName}`}
      >
        {children}
      </main>
      <NavBar items={getNavigationItems()} />
    </div>
  );
};

export default AppLayout;
