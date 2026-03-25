import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { RefreshCw } from "lucide-react";
import { Song } from "@/types/Song";
import { useSongs } from "@/hooks/api/useSongs";
import { toast } from "sonner";
import { createLogger } from "@/lib/logger";
import { useAuthStore } from "@/stores/authStore";

const logger = createLogger("component:reprocess");

const ENGINES = [
  {
    value: "three_track",
    label: "Three-Track",
    description: "Vocals + Backing + Instrumental",
  },
  { value: "demucs", label: "Demucs", description: "Standard quality, fast" },
  { value: "roformer", label: "Roformer", description: "High quality, fast" },
  { value: "hybrid", label: "Hybrid", description: "Best quality, slower" },
  {
    value: "clean_backing",
    label: "Clean Backing",
    description: "Cleanest backing vocals",
  },
];

interface ReprocessSectionProps {
  song: Song;
}

export const ReprocessSection: React.FC<ReprocessSectionProps> = ({ song }) => {
  const { useReprocessSong } = useSongs();
  const reprocessMutation = useReprocessSong();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const [selectedEngine, setSelectedEngine] = useState<string>(
    song.engineType || "demucs",
  );

  const handleReprocess = async () => {
    if (selectedEngine === song.engineType) {
      toast.error("Please select a different engine");
      return;
    }

    try {
      await reprocessMutation.mutateAsync({
        id: song.id,
        engine_type: selectedEngine,
      });
    } catch (error) {
      logger.error("Reprocess failed:", error);
      toast.error(
        error instanceof Error ? error.message : "Failed to start reprocessing",
      );
    }
  };

  const isProcessed = song.status === "processed";
  const isReprocessing = reprocessMutation.isPending;
  const isSameEngine = selectedEngine === song.engineType;

  const currentEngineLabel =
    ENGINES.find((e) => e.value === song.engineType)?.label || song.engineType;

  if (!isAuthenticated) return null;

  return (
    <div className="border-t pt-4 mt-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium">Re-process Audio</span>
        {song.engineType && (
          <span className="text-xs text-muted-foreground">
            Current: {currentEngineLabel}
          </span>
        )}
      </div>

      <div className="flex gap-3 items-center">
        <Select value={selectedEngine} onValueChange={setSelectedEngine}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Select engine" />
          </SelectTrigger>
          <SelectContent>
            {ENGINES.map((engine) => (
              <SelectItem key={engine.value} value={engine.value}>
                <div className="flex flex-col">
                  <span>{engine.label}</span>
                  <span className="text-xs text-muted-foreground">
                    {engine.description}
                  </span>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button
          variant="outline"
          onClick={handleReprocess}
          disabled={!isProcessed || isReprocessing || isSameEngine}
          className="flex items-center gap-2"
        >
          <RefreshCw
            size={16}
            className={isReprocessing ? "animate-spin" : ""}
          />
          {isReprocessing ? "Starting..." : "Re-process"}
        </Button>
      </div>

      {!isProcessed && (
        <p className="text-xs text-muted-foreground mt-2">
          Wait for current processing to complete before reprocessing
        </p>
      )}
      {isProcessed && isSameEngine && song.engineType && (
        <p className="text-xs text-muted-foreground mt-2">
          Select a different engine to re-process
        </p>
      )}
    </div>
  );
};
