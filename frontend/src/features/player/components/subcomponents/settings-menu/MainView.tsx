/**
 * MainView - Top-level settings menu with navigation to sub-views
 * Shows summary values for each setting category
 */

import React from "react";
import { ChevronRight, ScrollText, Volume2, Gauge, Guitar } from "lucide-react";
import { Settings2 } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { useAudioControlsStore } from "@/stores/useAudioControlsStore";
import { cn } from "@/lib/utils";
import type { MenuView } from "../SettingsMenu";

interface MainViewProps {
  onNavigate: (view: MenuView) => void;
}

const MainView: React.FC<MainViewProps> = ({ onNavigate }) => {
  const lyricsSize = useKaraokePlayerStore((state) => state.lyricsSize);
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
  const showChords = useKaraokePlayerStore((state) => state.showChords);
  const setShowChords = useKaraokePlayerStore((state) => state.setShowChords);
  const playbackSpeed = useAudioControlsStore((state) => state.playbackSpeed);

  const menuItems = [
    {
      id: "lyrics",
      icon: ScrollText,
      label: "Lyrics",
      summary: `${lyricsSize.charAt(0).toUpperCase() + lyricsSize.slice(1)} text · Timing & edit`,
      onClick: () => onNavigate("lyrics"),
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

        {/* Guitar chords inline toggle */}
        <div
          className={cn(
            "w-full px-4 py-3 flex items-center justify-between",
            "text-left",
          )}
        >
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <Guitar className="w-5 h-5 text-background/60 shrink-0" />
            <span className="text-sm font-medium text-background">
              Guitar Chords
            </span>
          </div>
          <Switch checked={showChords} onCheckedChange={setShowChords} />
        </div>
      </div>
    </div>
  );
};

export default MainView;
