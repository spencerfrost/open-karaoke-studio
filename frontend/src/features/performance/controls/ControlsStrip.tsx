/**
 * ControlsStrip - the stage's left rail: the channel strip a singer drives
 * with the mouse on the mic stand. The phone has its own layout
 * (PerformanceControlsPanel); the two share behaviour through the store and
 * useLyricsFixes, not layout.
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

interface ControlsStripProps {
  className?: string;
}

const ControlsStrip: React.FC<ControlsStripProps> = ({ className }) => {
  const [moreOpen, setMoreOpen] = useState(false);

  return (
    <div className={cn("flex min-h-0 flex-col gap-3", className)}>
      <MixCard className="flex-1" />
      <LyricsControlsCard />

      <Button
        variant="ghost"
        onClick={() => setMoreOpen(true)}
        className="h-11 w-full shrink-0 text-base text-foreground-dim hover:text-foreground"
      >
        <MoreHorizontal className="size-5" />
        More
      </Button>

      <MoreControlsSheet open={moreOpen} onOpenChange={setMoreOpen} />
    </div>
  );
};

export default ControlsStrip;
