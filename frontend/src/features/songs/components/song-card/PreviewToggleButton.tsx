import React from "react";
import { Volume2, VolumeX } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface PreviewToggleButtonProps {
  songTitle: string;
  isActive: boolean;
  onToggle: () => void;
}

/**
 * Explicit preview control for pointers that cannot hover.
 *
 * Always visible on touch devices, revealed on card hover or keyboard focus
 * elsewhere. Shares the hover path's state — both route through the same
 * `togglePreview`, so a tapped preview and a hovered one are the same preview.
 */
export const PreviewToggleButton: React.FC<PreviewToggleButtonProps> = ({
  songTitle,
  isActive,
  onToggle,
}) => {
  const handleClick = (e: React.MouseEvent) => {
    // The performer card opens its drawer on any card click.
    e.stopPropagation();
    onToggle();
  };

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      aria-label={
        isActive ? `Stop preview of ${songTitle}` : `Preview ${songTitle}`
      }
      aria-pressed={isActive}
      onClick={handleClick}
      className={cn(
        "absolute right-2 bottom-2 z-20 size-10 touch-manipulation rounded-full",
        "bg-overlay/50 text-foreground backdrop-blur-sm hover:bg-overlay/70",
        "opacity-0 transition-opacity focus-visible:opacity-100 group-hover:opacity-100",
        "[@media(hover:none)]:opacity-100",
        isActive && "opacity-100",
      )}
    >
      {isActive ? (
        <VolumeX className="size-5" />
      ) : (
        <Volume2 className="size-5" />
      )}
    </Button>
  );
};
