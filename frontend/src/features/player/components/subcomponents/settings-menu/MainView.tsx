/**
 * MainView - Top-level settings menu with navigation to sub-views
 * Shows summary values for each setting category
 */

import React from "react";
import { ChevronRight, ScrollText, Volume2, Gauge, FileText } from "lucide-react";
import { Settings2 } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { useAudioControlsStore } from "@/stores/useAudioControlsStore";
import type { LyricsSize } from "@/utils/performanceControls";
import { cn } from "@/lib/utils";
import type { MenuView } from "../SettingsMenu";

interface MainViewProps {
  onNavigate: (view: MenuView) => void;
}

const MainView: React.FC<MainViewProps> = ({ onNavigate }) => {
  const lyricsSize = useKaraokePlayerStore((state) => state.lyricsSize);
  const lyricsOffset = useKaraokePlayerStore((state) => state.lyricsOffset);
  const vocalVolume = useKaraokePlayerStore((state) => state.vocalVolume);
  const instrumentalVolume = useKaraokePlayerStore(
    (state) => state.instrumentalVolume,
  );
  const autoScrollEnabled = useKaraokePlayerStore(
    (state) => state.autoScrollEnabled,
  );
  const setAutoScrollEnabled = useKaraokePlayerStore(
    (state) => state.setAutoScrollEnabled,
  );
  const setLyricsSize = useKaraokePlayerStore(
    (state) => state.setLyricsSize,
  );
  const playbackSpeed = useAudioControlsStore((state) => state.playbackSpeed);

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
    {
      id: "volume",
      icon: Volume2,
      label: "Volume",
      summary: `Vocal ${Math.round(vocalVolume * 100)}%, Instrumental ${Math.round(instrumentalVolume * 100)}%`,
      onClick: () => onNavigate("volume"),
    },
    {
      id: "speed",
      icon: Gauge,
      label: "Speed",
      summary: `${playbackSpeed.toFixed(2)}x`,
      onClick: () => onNavigate("speed"),
    },
  ];

  return (
    <div className="py-2">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/10">
        <div className="flex items-center gap-2">
          <Settings2 className="w-5 h-5 text-orange-peel" />
          <h2 className="text-lg font-semibold">Settings</h2>
        </div>
      </div>

      {/* Menu Items */}
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

        {/* Lyrics size inline button group */}
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

        {/* Auto-scroll inline toggle */}
        <div
          className={cn(
            "w-full px-4 py-3 flex items-center justify-between",
            "text-left",
          )}
        >
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <Settings2 className="w-5 h-5 text-background/60 shrink-0" />
            <span className="text-sm font-medium text-background">
              Auto-scroll
            </span>
          </div>
          <Switch
            checked={autoScrollEnabled}
            onCheckedChange={setAutoScrollEnabled}
          />
        </div>
      </div>
    </div>
  );
};

export default MainView;
