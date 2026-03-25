/**
 * VolumeView - Volume controls for vocals and instrumental tracks
 * Handles lead vocals, backing vocals (if available), and instrumental
 */

import React from "react";
import { ChevronLeft } from "lucide-react";
import { Slider } from "@/components/ui/slider";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";

interface VolumeViewProps {
  onBack: () => void;
}

const VolumeView: React.FC<VolumeViewProps> = ({ onBack }) => {
  const vocalVolume = useKaraokePlayerStore((state) => state.vocalVolume);
  const backingVocalVolume = useKaraokePlayerStore(
    (state) => state.backingVocalVolume,
  );
  const backingVocalUrl = useKaraokePlayerStore(
    (state) => state.backingVocalUrl,
  );
  const instrumentalVolume = useKaraokePlayerStore(
    (state) => state.instrumentalVolume,
  );
  const setVocalVolume = useKaraokePlayerStore(
    (state) => state.setVocalVolume,
  );
  const setBackingVocalVolume = useKaraokePlayerStore(
    (state) => state.setBackingVocalVolume,
  );
  const setInstrumentalVolume = useKaraokePlayerStore(
    (state) => state.setInstrumentalVolume,
  );

  return (
    <div className="py-2">
      {/* Header with back button */}
      <div className="px-4 py-3 border-b border-white/10">
        <button
          onClick={onBack}
          className="flex items-center gap-2 hover:text-orange-peel transition-colors"
        >
          <ChevronLeft className="w-5 h-5" />
          <h2 className="text-lg font-semibold">Volume</h2>
        </button>
      </div>

      {/* Content */}
      <div className="px-4 py-4 space-y-4">
        {/* Vocal Volume */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label className="text-background">
              {backingVocalUrl ? "Lead Vocals" : "Vocals"}
            </Label>
            <span className="text-sm text-background/60">
              {Math.round(vocalVolume * 100)}%
            </span>
          </div>
          <Slider
            value={[vocalVolume]}
            onValueChange={([value]) => setVocalVolume(value)}
            min={0}
            max={1}
            step={0.05}
            className="w-full"
          />
        </div>

        {/* Backing Vocal Volume (only for three-track songs) */}
        {backingVocalUrl && (
          <>
            <Separator className="bg-white/10" />
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label className="text-background">Backing Vocals</Label>
                <span className="text-sm text-background/60">
                  {Math.round(backingVocalVolume * 100)}%
                </span>
              </div>
              <Slider
                value={[backingVocalVolume]}
                onValueChange={([value]) => setBackingVocalVolume(value)}
                min={0}
                max={1}
                step={0.05}
                className="w-full"
              />
            </div>
          </>
        )}

        <Separator className="bg-white/10" />

        {/* Instrumental Volume */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label className="text-background">Instrumental</Label>
            <span className="text-sm text-background/60">
              {Math.round(instrumentalVolume * 100)}%
            </span>
          </div>
          <Slider
            value={[instrumentalVolume]}
            onValueChange={([value]) => setInstrumentalVolume(value)}
            min={0}
            max={1}
            step={0.05}
            className="w-full"
          />
        </div>
      </div>
    </div>
  );
};

export default VolumeView;
