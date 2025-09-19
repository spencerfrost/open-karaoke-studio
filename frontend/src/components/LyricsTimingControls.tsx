import React from "react";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { Button } from "@/components/ui/button";
import { RotateCcw, Minus, Plus } from "lucide-react";
import KnobControl from "@/components/KnobControl";
import { getTimingOffsetDescription } from "@/utils/performanceControls";

const LyricsTimingControls: React.FC = () => {
  const { lyricsOffset, setLyricsOffset } = useKaraokePlayerStore();

  return (
    <div className="mt-6 space-y-4">
      <h3 className="text-lg font-semibold text-lemon-chiffon text-center">
        Lyrics Timing
      </h3>

      {/* Knob Control for Lyrics Offset */}
      <div className="flex justify-center">
        <KnobControl
          value={lyricsOffset}
          onChange={setLyricsOffset}
          min={-5000}
          max={5000}
          step={25}
          sensitivity={1.5}
          label="Offset"
          unit="ms"
          onReset={() => setLyricsOffset(0)}
        />
      </div>

      {/* Quick Adjustment Buttons */}
      <div className="flex items-center justify-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setLyricsOffset(lyricsOffset - 200)}
          className="flex items-center gap-1"
        >
          <Minus size={16} />
          200ms
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setLyricsOffset(lyricsOffset - 50)}
          className="flex items-center gap-1"
        >
          <Minus size={16} />
          50ms
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setLyricsOffset(0)}
          className="flex items-center gap-1 bg-orange-peel/20 hover:bg-orange-peel/30"
        >
          <RotateCcw size={16} />
          Reset
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setLyricsOffset(lyricsOffset + 50)}
          className="flex items-center gap-1"
        >
          <Plus size={16} />
          50ms
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setLyricsOffset(lyricsOffset + 200)}
          className="flex items-center gap-1"
        >
          <Plus size={16} />
          200ms
        </Button>
      </div>

      {/* Help Text */}
      <p className="text-xs text-lemon-chiffon/60 text-center">
        {getTimingOffsetDescription(lyricsOffset)}
      </p>
    </div>
  );
};

export default LyricsTimingControls;