import React, { useState, useEffect } from "react";
import { Song } from "@/types/Song";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useApiMutation } from "@/hooks/api/useApi";
import { Pencil, Check, X } from "lucide-react";

interface BpmEditorProps {
  song: Song;
}

export const BpmEditor: React.FC<BpmEditorProps> = ({ song }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [bpmValue, setBpmValue] = useState(song.bpm?.toString() ?? "");
  const [tapTimes, setTapTimes] = useState<number[]>([]);

  const updateSongMutation = useApiMutation<Song, { id: string; bpm: number }>(
    "PATCH",
    (variables) => `/api/songs/${variables.id}`,
    {
      invalidateQueries: ["songs", `song-${song.id}`],
    }
  );

  useEffect(() => {
    // Update local state when song prop changes
    setBpmValue(song.bpm?.toString() ?? "");
  }, [song.bpm]);

  useEffect(() => {
    // Reset tap times after 2 seconds of inactivity
    if (tapTimes.length > 0) {
      const timer = setTimeout(() => setTapTimes([]), 2000);
      return () => clearTimeout(timer);
    }
  }, [tapTimes]);

  const handleSave = async () => {
    const bpm = parseFloat(bpmValue);
    if (bpm >= 30 && bpm <= 300 && !isNaN(bpm)) {
      await updateSongMutation.mutateAsync({ id: song.id, bpm });
      setIsEditing(false);
    }
  };

  const handleCancel = () => {
    setBpmValue(song.bpm?.toString() ?? "");
    setTapTimes([]);
    setIsEditing(false);
  };

  const handleTapTempo = () => {
    const now = Date.now();
    const newTaps = [...tapTimes, now].slice(-4); // Keep last 4 taps
    setTapTimes(newTaps);

    if (newTaps.length >= 2) {
      // Calculate average interval between taps
      const intervals = [];
      for (let i = 1; i < newTaps.length; i++) {
        intervals.push(newTaps[i] - newTaps[i - 1]);
      }
      const avgInterval = intervals.reduce((a, b) => a + b) / intervals.length;
      const calculatedBpm = 60000 / avgInterval;
      setBpmValue(calculatedBpm.toFixed(1));
    }
  };

  const bpmValid = () => {
    const bpm = parseFloat(bpmValue);
    return !isNaN(bpm) && bpm >= 30 && bpm <= 300;
  };

  if (!isEditing) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground">BPM:</span>
        <span className="font-medium">
          {song.bpm?.toFixed(1) ?? "Unknown"}
        </span>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsEditing(true)}
          className="h-7 px-2"
        >
          <Pencil size={14} />
        </Button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <span className="text-sm text-muted-foreground">BPM:</span>
      <Input
        type="number"
        min={30}
        max={300}
        step={0.1}
        value={bpmValue}
        onChange={(e) => setBpmValue(e.target.value)}
        className="w-24 h-8"
        placeholder="80-180"
      />
      <Button
        variant="outline"
        size="sm"
        onClick={handleTapTempo}
        className={`h-8 ${tapTimes.length > 0 ? "bg-orange-peel/10" : ""}`}
        title="Tap 2-4 times to the beat"
      >
        Tap ({tapTimes.length}/4)
      </Button>
      <Button
        variant="default"
        size="sm"
        onClick={handleSave}
        disabled={!bpmValid() || updateSongMutation.isPending}
        className="h-8"
      >
        <Check size={14} />
      </Button>
      <Button
        variant="ghost"
        size="sm"
        onClick={handleCancel}
        disabled={updateSongMutation.isPending}
        className="h-8"
      >
        <X size={14} />
      </Button>
      {!bpmValid() && bpmValue && (
        <span className="text-xs text-red-500">BPM must be 30-300</span>
      )}
    </div>
  );
};
