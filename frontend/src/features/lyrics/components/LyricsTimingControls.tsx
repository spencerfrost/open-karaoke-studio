import React from "react";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { Button } from "@/components/ui/button";
import { RotateCcw, Minus, Plus } from "lucide-react";
import KnobControl from "@/features/performance/components/KnobControl";

interface LyricsTimingControlsProps {}

const LyricsTimingControls: React.FC<LyricsTimingControlsProps> = () => {
  const { lyricsOffset, setLyricsOffset } = useKaraokePlayerStore();

  return (
    <div className="flex flex-col items-stretch justify-center gap-3">
      <div className="text-xs text-center text-lemon-chiffon/80">
        Lyrics Timing
      </div>
      {/* Knob */}
      <KnobControl
        value={lyricsOffset}
        onChange={setLyricsOffset}
        min={-5000}
        max={5000}
        step={25}
        sensitivity={1.5}
        label=""
        unit="ms"
        size="xl"
      />

      {/* Quick Adjustment Buttons - Column */}
      <div className="flex flex-col gap-2">
        <Button
          variant="outline"
          onClick={() => setLyricsOffset(lyricsOffset + 50)}
        >
          <Plus size={12} />
          50
        </Button>
        <Button
          variant="outline"
          onClick={() => setLyricsOffset(0)}
          className="bg-orange-peel/20 hover:bg-orange-peel/30"
        >
          <RotateCcw size={12} />
        </Button>
        <Button
          variant="outline"
          onClick={() => setLyricsOffset(lyricsOffset - 50)}
        >
          <Minus size={12} />
          50
        </Button>
      </div>
    </div>
  );
};

export default LyricsTimingControls;
