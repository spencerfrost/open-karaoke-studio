/**
 * MixCard - the two faders the singer reaches for first: vocals and backing.
 */

import React from "react";
import { Mic, Music, SlidersHorizontal } from "lucide-react";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { usePerformanceControlsLogic } from "../hooks/usePerformanceControlsLogic";
import VocalFader from "./VocalFader";
import {
  cardClass,
  cardIconClass,
  cardLabelClass,
  type Density,
} from "./density";
import { cn } from "@/lib/utils";

interface MixCardProps {
  density: Density;
  className?: string;
}

const MixCard: React.FC<MixCardProps> = ({ density, className }) => {
  const {
    vocalVolume,
    backingVocalVolume,
    toggleVocalsVolume,
    toggleBackingVocalsVolume,
    setVocalVolume,
    setBackingVocalVolume,
  } = usePerformanceControlsLogic();

  // Two-track songs have no separate backing vocal stem.
  const backingVocalUrl = useKaraokePlayerStore(
    (state) => state.backingVocalUrl,
  );
  const backingAvailable = !!backingVocalUrl;

  return (
    // overflow-hidden: the faders shrink with the card, but on a viewport too
    // short even for that they must clip rather than draw over the lyrics card.
    <div
      className={cardClass(density, cn("min-h-0 overflow-hidden", className))}
    >
      <div className="flex items-center gap-2.5">
        <SlidersHorizontal
          className={cn(cardIconClass(density), "text-primary")}
        />
        <span className={cardLabelClass(density)}>Mix</span>
      </div>

      <div
        className={cn(
          "grid min-h-0 flex-1 grid-cols-2",
          density === "tv" ? "gap-2" : "gap-3.5",
        )}
      >
        <VocalFader
          label="Vocals"
          icon={<Mic />}
          volume={vocalVolume}
          onVolumeChange={setVocalVolume}
          onToggleMute={toggleVocalsVolume}
          density={density}
        />
        <VocalFader
          label="Backing"
          icon={<Music />}
          volume={backingAvailable ? backingVocalVolume : 0}
          onVolumeChange={setBackingVocalVolume}
          onToggleMute={toggleBackingVocalsVolume}
          density={density}
          disabled={!backingAvailable}
          disabledHint="No backing track"
        />
      </div>
    </div>
  );
};

export default MixCard;
