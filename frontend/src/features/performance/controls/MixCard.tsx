/**
 * MixCard - the two faders the singer reaches for first: vocals and backing.
 */

import React from "react";
import { Mic, Music, SlidersHorizontal } from "lucide-react";
import { useBackingTrackAvailable } from "../hooks/useBackingTrackAvailable";
import { usePerformanceControlsLogic } from "../hooks/usePerformanceControlsLogic";
import VocalFader from "./VocalFader";
import { cardClass, cardIconClass, cardLabelClass } from "./cardStyles";
import { cn } from "@/lib/utils";

interface MixCardProps {
  className?: string;
}

const MixCard: React.FC<MixCardProps> = ({ className }) => {
  const {
    vocalVolume,
    backingVocalVolume,
    toggleVocalsVolume,
    toggleBackingVocalsVolume,
    setVocalVolume,
    setBackingVocalVolume,
  } = usePerformanceControlsLogic();
  const backingAvailable = useBackingTrackAvailable();

  return (
    // overflow-hidden: the faders shrink with the card, but on a viewport too
    // short even for that they must clip rather than draw over the lyrics card.
    <div className={cardClass(cn("min-h-0 overflow-hidden", className))}>
      <div className="flex items-center gap-2.5">
        <SlidersHorizontal className={cn(cardIconClass, "text-primary")} />
        <span className={cardLabelClass}>Mix</span>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-2 gap-2">
        <VocalFader
          label="Vocals"
          tourId="vocal-level"
          icon={<Mic />}
          volume={vocalVolume}
          onVolumeChange={setVocalVolume}
          onToggleMute={toggleVocalsVolume}
        />
        <VocalFader
          label="Backing"
          icon={<Music />}
          volume={backingAvailable ? backingVocalVolume : 0}
          onVolumeChange={setBackingVocalVolume}
          onToggleMute={toggleBackingVocalsVolume}
          disabled={!backingAvailable}
          disabledHint="No backing track"
        />
      </div>
    </div>
  );
};

export default MixCard;
