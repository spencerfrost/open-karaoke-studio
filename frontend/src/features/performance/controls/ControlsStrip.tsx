/**
 * ControlsStrip - the single channel strip rendered by BOTH the stage's left
 * rail (density="tv") and the performer's phone (density="touch").
 *
 * Same order, same components, same tokens; only the type scale and hit areas
 * differ. Keeping one composition is what stops the two surfaces drifting.
 *
 * Order is control priority: vocals -> backing -> lyrics search -> offset ->
 * size -> everything else, behind More.
 */

import React, { useState } from "react";
import { MoreHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import MixCard from "./MixCard";
import LyricsControlsCard from "./LyricsControlsCard";
import MoreControlsSheet from "./MoreControlsSheet";
import type { Density } from "./density";

interface ControlsStripProps {
  density: Density;
  className?: string;
}

const ControlsStrip: React.FC<ControlsStripProps> = ({
  density,
  className,
}) => {
  const isTv = density === "tv";
  const [moreOpen, setMoreOpen] = useState(false);

  return (
    <div
      className={cn(
        "flex min-h-0 flex-col",
        isTv ? "gap-3" : "gap-2.5",
        className,
      )}
    >
      <MixCard density={density} className="flex-1" />
      <LyricsControlsCard density={density} />

      <Button
        variant="ghost"
        onClick={() => setMoreOpen(true)}
        className={cn(
          "w-full shrink-0 text-foreground/55 hover:text-foreground",
          isTv ? "h-11 text-base" : "h-12 text-sm",
        )}
      >
        <MoreHorizontal className="size-5" />
        More
      </Button>

      <MoreControlsSheet
        open={moreOpen}
        onOpenChange={setMoreOpen}
        density={density}
      />
    </div>
  );
};

export default ControlsStrip;
