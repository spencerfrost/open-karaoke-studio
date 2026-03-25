import React from "react";
import { Button } from "@/components/ui/button";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";

const LyricsSizeControl: React.FC = () => {
  const { lyricsSize, setLyricsSize } = useKaraokePlayerStore();

  return (
    <div className="flex flex-col items-stretch gap-2">
      <div className="text-xs text-center text-lemon-chiffon/80">
        Lyrics Size
      </div>
      <div className="flex">
        <Button
          variant={lyricsSize === "small" ? "default" : "outline"}
          onClick={() => setLyricsSize("small")}
          size="sm"
          className="flex-1 rounded-r-none border-r-0 font-semibold"
        >
          S
        </Button>
        <Button
          variant={lyricsSize === "medium" ? "default" : "outline"}
          onClick={() => setLyricsSize("medium")}
          size="sm"
          className="flex-1 rounded-none font-semibold"
        >
          M
        </Button>
        <Button
          variant={lyricsSize === "large" ? "default" : "outline"}
          onClick={() => setLyricsSize("large")}
          size="sm"
          className="flex-1 rounded-l-none border-l-0 font-semibold"
        >
          L
        </Button>
      </div>
    </div>
  );
};

export default LyricsSizeControl;
