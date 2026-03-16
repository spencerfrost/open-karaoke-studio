/**
 * LyricsView - Lyrics settings submenu
 * Groups Lyrics Timing, Edit Lyrics, and Text Size under a single submenu
 */

import React from "react";
import { ChevronLeft, ChevronRight, ScrollText, FileText } from "lucide-react";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import type { LyricsSize } from "@/utils/performanceControls";
import { cn } from "@/lib/utils";
import type { MenuView } from "../SettingsMenu";

interface LyricsViewProps {
  onBack: () => void;
  onNavigate: (view: MenuView) => void;
}

const LyricsView: React.FC<LyricsViewProps> = ({ onBack, onNavigate }) => {
  const lyricsSize = useKaraokePlayerStore((state) => state.lyricsSize);
  const setLyricsSize = useKaraokePlayerStore((state) => state.setLyricsSize);

  const menuItems = [
    {
      id: "lyricsTiming",
      icon: ScrollText,
      label: "Lyrics Timing",
      summary: "Fine-tune lyrics sync",
      onClick: () => onNavigate("lyricsTiming"),
    },
    {
      id: "lyricsEdit",
      icon: FileText,
      label: "Edit Lyrics",
      summary: "Modify or fetch lyrics",
      onClick: () => onNavigate("lyricsEdit"),
    },
  ];

  return (
    <div className="py-2">
      {/* Header with back button */}
      <div className="px-4 py-3 border-b border-white/10">
        <button
          onClick={onBack}
          className="flex items-center gap-2 hover:text-orange-peel transition-colors"
        >
          <ChevronLeft className="w-5 h-5" />
          <h2 className="text-lg font-semibold">Lyrics</h2>
        </button>
      </div>

      {/* Nav items */}
      <div className="py-2">
        {menuItems.map((item) => (
          <button
            key={item.id}
            onClick={item.onClick}
            className={cn(
              "w-full px-4 py-3 flex items-center justify-between",
              "hover:bg-white/5 active:bg-white/10 transition-colors",
              "text-left group",
            )}
          >
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <item.icon className="w-5 h-5 text-background/60 shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-background">
                  {item.label}
                </div>
                <div className="text-xs text-background/40 truncate">
                  {item.summary}
                </div>
              </div>
            </div>
            <ChevronRight className="w-4 h-4 text-background/40 group-hover:text-background/60 shrink-0" />
          </button>
        ))}

        {/* Text Size inline button group */}
        <div
          className={cn(
            "w-full px-4 py-3 flex items-center justify-between",
            "text-left",
          )}
        >
          <div className="flex items-center gap-3 min-w-0">
            <ScrollText className="w-5 h-5 text-background/60 shrink-0" />
            <span className="text-sm font-medium text-background">
              Text Size
            </span>
          </div>
          <div className="flex rounded-md overflow-hidden border border-white/10">
            {(["small", "medium", "large"] as LyricsSize[]).map((size) => (
              <button
                key={size}
                onClick={() => setLyricsSize(size)}
                className={cn(
                  "px-2.5 py-1 text-xs font-medium transition-colors",
                  lyricsSize === size
                    ? "bg-orange-peel text-black"
                    : "text-background/60 hover:bg-white/10 hover:text-background",
                )}
              >
                {size === "small" ? "S" : size === "medium" ? "M" : "L"}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LyricsView;
