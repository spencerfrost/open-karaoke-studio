/**
 * SettingsMenu - YouTube-style popover settings menu for player controls
 * Supports nested navigation with stack-based view management
 * Non-modal to allow interaction with rest of player while open
 */

import React, { useState, useEffect } from "react";
import { Settings2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import MainView from "./settings-menu/MainView.js";
import VolumeView from "./settings-menu/VolumeView.js";
import SpeedView from "./settings-menu/SpeedView.js";
import { motion, AnimatePresence } from "framer-motion";
import LyricsEditView from "./settings-menu/LyricsEditView.js";
import LyricsTimingView from "./settings-menu/LyricsTimingView.js";

export type MenuView = "main" | "lyricsTiming" | "lyricsEdit" | "volume" | "speed";

interface SettingsMenuProps {
  className?: string;
}

export const SettingsMenu: React.FC<SettingsMenuProps> = ({ className }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [viewStack, setViewStack] = useState<MenuView[]>(["main"]);
  const [fsContainer, setFsContainer] = useState<HTMLElement | null>(null);

  useEffect(() => {
    // Initialize from current state in case we mounted while already in fullscreen
    setFsContainer((document.fullscreenElement as HTMLElement) ?? null);

    const handleFullscreenChange = () => {
      setFsContainer((document.fullscreenElement as HTMLElement) ?? null);
    };
    document.addEventListener("fullscreenchange", handleFullscreenChange);
    document.addEventListener("webkitfullscreenchange", handleFullscreenChange);
    return () => {
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
      document.removeEventListener("webkitfullscreenchange", handleFullscreenChange);
    };
  }, []);

  const currentView = viewStack[viewStack.length - 1];

  const navigateTo = (view: MenuView) => {
    setViewStack((prev) => [...prev, view]);
  };

  const navigateBack = () => {
    setViewStack((prev) => {
      if (prev.length <= 1) return prev; // Always keep at least one view
      return prev.slice(0, -1);
    });
  };

  const resetToMain = () => {
    setViewStack(["main"]);
  };

  // Reset view stack when menu closes
  const handleOpenChange = (open: boolean) => {
    setIsOpen(open);
    if (!open) {
      resetToMain();
    }
  };

  const contentVariants = {
    enter: {
      opacity: 0,
    },
    center: {
      opacity: 1,
    },
    exit: {
      opacity: 0,
      position: "absolute" as const,
      top: 0,
      left: 0,
      right: 0,
    },
  };

  const renderView = () => {
    switch (currentView) {
      case "main":
        return <MainView onNavigate={navigateTo} />;
      case "lyricsTiming":
        return <LyricsTimingView onBack={navigateBack} />;
      case "lyricsEdit":
        return <LyricsEditView onBack={navigateBack} />;
      case "volume":
        return <VolumeView onBack={navigateBack} />;
      case "speed":
        return <SpeedView onBack={navigateBack} />;
      default:
        return <MainView onNavigate={navigateTo} />;
    }
  };

  return (
    <Popover open={isOpen} onOpenChange={handleOpenChange} modal={false}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className={cn(
            "text-background/60 hover:text-background hover:bg-white/10",
            className,
          )}
          aria-label="Open settings"
        >
          <Settings2 className="w-5 h-5" />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        align="start"
        alignOffset={-96}
        side="top"
        sideOffset={16}
        className="w-80 p-0 border-none bg-transparent shadow-none overflow-visible"
        container={fsContainer}
      >
        <motion.div
          layout
          transition={{
            layout: { type: "spring", stiffness: 400, damping: 30 },
          }}
          className="relative flex flex-col justify-end rounded-md bg-black/95 backdrop-blur-md border border-white/10 text-background overflow-hidden"
        >
          <AnimatePresence initial={false}>
            <motion.div
              key={currentView}
              variants={contentVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.15 }}
            >
              {renderView()}
            </motion.div>
          </AnimatePresence>
        </motion.div>
      </PopoverContent>
    </Popover>
  );
};

// Export trigger separately if needed elsewhere
export const SettingsMenuTrigger: React.FC<{
  onClick: () => void;
  className?: string;
}> = ({ onClick, className }) => (
  <Button
    variant="ghost"
    size="icon"
    onClick={onClick}
    className={cn(
      "text-background/60 hover:text-background hover:bg-white/10",
      className,
    )}
    aria-label="Open settings"
  >
    <Settings2 className="w-5 h-5" />
  </Button>
);
