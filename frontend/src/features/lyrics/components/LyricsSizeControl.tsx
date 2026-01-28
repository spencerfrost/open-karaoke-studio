import React from "react";
import { Button } from "@/components/ui/button";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";

const LyricsSizeControl: React.FC = () => {
  const { lyricsSize, setLyricsSize } = useKaraokePlayerStore();

  return (
    <div className="flex flex-col items-stretch gap-4">
      <div className="text-xs text-center text-lemon-chiffon/80">
        Lyrics Size
      </div>
      <div className="flex flex-col gap-3">
        <Button
          variant={lyricsSize === "small" ? "default" : "outline"}
          onClick={() => setLyricsSize("small")}
          size="sm"
          className="font-semibold mx-4"
        >
          S
        </Button>
        <Button
          variant={lyricsSize === "medium" ? "default" : "outline"}
          onClick={() => setLyricsSize("medium")}
          className="font-semibold mx-2"
        >
          M
        </Button>
        <Button
          variant={lyricsSize === "large" ? "default" : "outline"}
          onClick={() => setLyricsSize("large")}
          size="lg"
          className="font-semibold"
        >
          L
        </Button>
      </div>
    </div>
  );
};

export default LyricsSizeControl;
