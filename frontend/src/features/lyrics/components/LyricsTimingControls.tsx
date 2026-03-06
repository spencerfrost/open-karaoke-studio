import React from "react";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { Button } from "@/components/ui/button";
import { RotateCcw, Minus, Plus } from "lucide-react";
import KnobControl from "@/features/performance/components/KnobControl";

interface LyricsTimingControlsProps { }

const LyricsTimingControls: React.FC<LyricsTimingControlsProps> = () => {
  const { lyricsOffset, setLyricsOffset } = useKaraokePlayerStore();

  return (
    <div className="flex flex-col items-stretch justify-center gap-3">
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
      <div className="flex items-center justify-center gap-2">
        <Button
          className="gap-0"
          variant="outline-dark"
          onClick={() => setLyricsOffset(lyricsOffset - 100)}
        >
          -100
        </Button>
        <Button
          variant="outline-dark"
          onClick={() => setLyricsOffset(lyricsOffset - 50)}
        >
          -50
        </Button>

        {/* Reset Timing */}
        <Button
          onClick={() => setLyricsOffset(0)}
          variant="ghost"
          size="auto"
        >
          <RotateCcw size="24" />
        </Button>

        <Button
          variant="outline-dark"
          onClick={() => setLyricsOffset(lyricsOffset + 100)}
        >
          +50
        </Button>
        <Button
          variant="outline-dark"
          className="gap-0"
          onClick={() => setLyricsOffset(lyricsOffset + 50)}
        >
          +100
        </Button>
      </div>
    </div>
  );
};

export default LyricsTimingControls;
