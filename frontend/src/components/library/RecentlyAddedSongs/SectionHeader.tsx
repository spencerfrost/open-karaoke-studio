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
      <span className="text-xl font-semibold text-orange-peel">
        Recently Added
      </span>
      {hasNextPage && (
        <Button
          variant="ghost"
          size="icon"
          onClick={onNext}
          disabled={isAnimating}
          title={`Show next ${songsPerPage} songs`}
          className="text-orange-peel hover:bg-orange-peel/20 disabled:opacity-50"
        >
          <ChevronRight size={20} />
        </Button>
      )}
    </div>
  );
};