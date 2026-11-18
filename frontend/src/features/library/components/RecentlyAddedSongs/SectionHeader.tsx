import React from "react";
import { Button } from "@/components/ui/button";
import { ChevronRight } from "lucide-react";

interface SectionHeaderProps {
  hasNextPage: boolean;
  isAnimating: boolean;
  onNext: () => void;
  songsPerPage: number;
}

export const SectionHeader: React.FC<SectionHeaderProps> = ({
  hasNextPage,
  isAnimating,
  onNext,
  songsPerPage,
}) => {
  return (
    <div className="flex items-center justify-between mb-4">
      <span className="text-xl font-semibold text-section-label">
        Recently Added
      </span>
      {hasNextPage && (
        <Button
          variant="ghost"
          size="icon"
          onClick={onNext}
          disabled={isAnimating}
          title={`Show next ${songsPerPage} songs`}
          className="text-foreground-dim hover:bg-surface-hover hover:text-foreground disabled:opacity-50"
        >
          <ChevronRight size={20} />
        </Button>
      )}
    </div>
  );
};
