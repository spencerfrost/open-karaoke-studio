/**
 * MixCard - the faders the singer reaches for first: vocals and backing, plus
 * their own headphones when the stage has a headphones output.
 */

import React from "react";
import { Headphones, Mic, Music, SlidersHorizontal } from "lucide-react";
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
    headphonesVolume,
    headphonesAvailable,
    toggleVocalsVolume,
    toggleBackingVocalsVolume,
    toggleHeadphonesVolume,
    setVocalVolume,
    setBackingVocalVolume,
    setHeadphonesVolume,
  } = usePerformanceControlsLogic();
  const backingAvailable = useBackingTrackAvailable();

  return (
    // overflow-hidden: the faders shrink with the card, but on a viewport too
    // short even for that they must clip rather than draw over the lyrics card.
    <div className={cardClass(cn("min-h-0 overflow-hidden", className))}>
      <div className="flex items-center gap-2.5">
        <SlidersHorizontal className={cn(cardIconClass, "text-secondary")} />
        <span className={cardLabelClass}>Mix</span>
      </div>

      <div
        className={cn(
          "grid min-h-0 flex-1 gap-2",
          headphonesAvailable ? "grid-cols-3" : "grid-cols-2",
        )}
      >
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
        {headphonesAvailable && (
          <VocalFader
            label="Headphones"
            icon={<Headphones />}
            volume={headphonesVolume}
            onVolumeChange={setHeadphonesVolume}
            onToggleMute={toggleHeadphonesVolume}
          />
        )}
      </div>
    </div>
  );
};

export default MixCard;
