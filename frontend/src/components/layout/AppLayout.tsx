import React, { ReactNode } from "react";
import NavBar, { type NavItem } from "./NavBar";
import {
  Music,
  Upload,
  List,
  Sliders,
  ShieldCheck,
  Waves,
  Settings,
} from "lucide-react";
import { useAccess } from "@/hooks/useAccess";

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
  const access = useAccess();

  // Tabs mirror routes/guards.tsx's capability checks exactly, so nothing
  // shown here is a dead end.
  const getNavigationItems = () => {
    const items: NavItem[] = [
      { name: "Library", path: "/", icon: Music },
      { name: "Add", path: "/add", icon: Upload },
    ];

    // A host account can always reach /stage - it's what creates a session,
    // so it isn't gated on having one. Highlighted once this device is the
    // one actually running the night.
    if (access.isHost) {
      items.push({
        name: "Stage",
        path: "/stage",
        icon: List,
        highlight: access.inSession && access.isStageDevice,
      });
    }

    // Any non-stage device in a live session can reach /controls, host or not.
    if (access.inSession && !access.isStageDevice) {
      items.push({ name: "Controls", path: "/controls", icon: Sliders });
    }

    // Settings is where the account lives - so any account holder needs it
    // reachable, not just a host.
    if (access.isAuthenticated) {
      items.push({ name: "Settings", path: "/settings", icon: Settings });
    }

    if (access.isAdmin) {
      items.push({ name: "Admin", path: "/admin", icon: ShieldCheck });
      items.push({
        name: "Compare",
        path: "/admin/compare-three-track",
        icon: Waves,
      });
    }

    return items;
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
