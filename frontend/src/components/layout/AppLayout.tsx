import React, { ReactNode } from "react";
import NavBar, { type NavItem } from "./NavBar";
import { AccountMenu } from "@/features/session";
import {
  Music,
  Upload,
  List,
  Sliders,
  ShieldCheck,
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
  /**
   * Leave out the bottom nav and the account menu. For a full-screen tool that
   * has its own way out (the singer's controls), where every pixel goes to the
   * controls.
   */
  hideNav?: boolean;
}

const AppLayout: React.FC<AppLayoutProps> = ({
  children,
  contentClassName = "p-2 sm:p-4",
  hideNav = false,
}) => {
  const access = useAccess();

  // Tabs mirror routes/guards.tsx's capability checks exactly, so nothing
  // shown here is a dead end.
  const getNavigationItems = () => {
    const items: NavItem[] = [
      { name: "Songbook", path: "/", icon: Music },
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

    // Settings belongs to any account holder, not just a host.
    if (access.isAuthenticated) {
      items.push({ name: "Settings", path: "/settings", icon: Settings });
    }

    if (access.isAdmin) {
      items.push({ name: "Admin", path: "/admin", icon: ShieldCheck });
    }

    return items;
  };

  return (
    // Keep the nav clear of the phone's home indicator
    <div className="flex flex-col h-dvh pb-[env(safe-area-inset-bottom)]">
      <div className="theme-texture" />
      <div className="theme-pattern" />
      <main
        className={`flex-1 overflow-auto relative z-10 ${contentClassName}`}
      >
        {/* In the page's flow until there's a margin wide enough to float in. */}
        {!hideNav && (
          <AccountMenu className="lg:absolute lg:top-2 lg:right-3 lg:z-30" />
        )}
        {children}
      </main>
      {!hideNav && <NavBar items={getNavigationItems()} />}
    </div>
  );
};

export default AppLayout;
