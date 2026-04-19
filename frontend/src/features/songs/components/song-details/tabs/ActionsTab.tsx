import React, { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Song } from "@/types/Song";
import { useSongs } from "@/hooks/api/useSongs";
import { useAuthStore } from "@/stores/authStore";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { createLogger } from "@/lib/logger";
import { FingerprintLookupPanel } from "@/features/songs/components/admin/panels/FingerprintLookupPanel";
import { MusicBrainzSearchPanel } from "@/features/songs/components/admin/panels/MusicBrainzSearchPanel";
import { YouTubeMusicReplacePanel } from "@/features/songs/components/admin/panels/YouTubeMusicReplacePanel";
import { UploadReplacePanel } from "@/features/songs/components/admin/panels/UploadReplacePanel";

const logger = createLogger("component:ActionsTab");

type ActiveAction = "fingerprint" | "musicbrainz" | "replace-yt" | "replace-upload" | null;

const ENGINE_OPTIONS = [
  { value: "three_track", label: "Three Track" },
  { value: "demucs", label: "Demucs" },
  { value: "roformer", label: "Roformer" },
  { value: "hybrid", label: "Hybrid" },
  { value: "clean_backing", label: "Clean Backing" },
] as const;

type EngineType = (typeof ENGINE_OPTIONS)[number]["value"];

interface ActionsTabProps {
  song: Song;
  onDone: () => void;
}

export const ActionsTab: React.FC<ActionsTabProps> = ({ song, onDone }) => {
  const queryClient = useQueryClient();
  const { token } = useAuthStore();
  const { useReprocessSong } = useSongs();

  const [activeAction, setActiveAction] = useState<ActiveAction>(null);
  const [showReprocess, setShowReprocess] = useState(false);
  const [selectedEngine, setSelectedEngine] = useState<EngineType>("demucs");

  const toggle = (action: ActiveAction) =>
    setActiveAction((prev) => (prev === action ? null : action));

  const reprocessMutation = useReprocessSong();

  const analyzeVocalRangeMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(`/api/songs/${song.id}/analyze-vocal-range`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail ?? "Vocal range analysis failed");
      }
      return res.json() as Promise<{ vocal_range_low: string; vocal_range_high: string }>;
    },
    onSuccess: (data) => {
      toast.success(`Vocal range: ${data.vocal_range_low} – ${data.vocal_range_high}`);
      onDone();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const skipMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(`/api/songs/${song.id}/skip-fingerprint`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to skip");
    },
    onSuccess: () => {
      toast.success("Fingerprint skipped");
      onDone();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const handleReprocessConfirm = () => {
    logger.info("reprocessing song %s with engine %s", song.id, selectedEngine);
    reprocessMutation.mutate(
      { id: song.id, engine_type: selectedEngine },
      {
        onSuccess: () => {
          toast.success("Reprocess job queued");
          setShowReprocess(false);
          onDone();
        },
        onError: (e: Error) => toast.error(e.message),
      },
    );
  };

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
          Identify Song
        </p>
        <div className="flex flex-wrap gap-2">
          <Button
            variant={activeAction === "fingerprint" ? "default" : "outline"}
            size="sm"
            onClick={() => toggle("fingerprint")}
          >
            Fingerprint Lookup
          </Button>
          <Button
            variant={activeAction === "musicbrainz" ? "default" : "outline"}
            size="sm"
            onClick={() => toggle("musicbrainz")}
          >
            MusicBrainz Search
          </Button>
        </div>
      </div>

      <div>
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
          Replace Song
        </p>
        <div className="flex flex-wrap gap-2">
          <Button
            variant={activeAction === "replace-yt" ? "default" : "outline"}
            size="sm"
            onClick={() => toggle("replace-yt")}
          >
            Replace from YouTube Music
          </Button>
          <Button
            variant={activeAction === "replace-upload" ? "default" : "outline"}
            size="sm"
            onClick={() => toggle("replace-upload")}
          >
            Upload MP3
          </Button>
        </div>
      </div>

      <div>
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
          Analyze
        </p>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={analyzeVocalRangeMutation.isPending}
            onClick={() => analyzeVocalRangeMutation.mutate()}
          >
            {analyzeVocalRangeMutation.isPending ? "Analyzing…" : "Analyze Vocal Range"}
          </Button>
        </div>
      </div>

      <div>
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
          Advanced
        </p>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            size="sm"
            disabled={reprocessMutation.isPending}
            onClick={() => setShowReprocess((prev) => !prev)}
          >
            {reprocessMutation.isPending ? "Reprocessing…" : "Reprocess Audio"}
          </Button>
          <Button
            variant="secondary"
            size="sm"
            disabled={skipMutation.isPending}
            onClick={() => skipMutation.mutate()}
          >
            Skip Fingerprint
          </Button>
        </div>
      </div>

      <div className="mt-4 space-y-2">
        {activeAction === "fingerprint" && (
          <FingerprintLookupPanel
            song={song}
            onDone={() => {
              queryClient.invalidateQueries({ queryKey: ["admin-acoustid-songs"] });
              onDone();
            }}
          />
        )}
        {activeAction === "musicbrainz" && (
          <MusicBrainzSearchPanel song={song} onDone={onDone} />
        )}
        {activeAction === "replace-yt" && (
          <YouTubeMusicReplacePanel song={song} onDone={onDone} />
        )}
        {activeAction === "replace-upload" && (
          <UploadReplacePanel song={song} onDone={onDone} />
        )}
        {showReprocess && (
          <div className="border rounded-md p-3 space-y-3">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Select Engine
            </p>
            <select
              value={selectedEngine}
              onChange={(e) => setSelectedEngine(e.target.value as EngineType)}
              className="w-full rounded-md border bg-background px-3 py-1.5 text-sm"
            >
              {ENGINE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <Button
              size="sm"
              disabled={reprocessMutation.isPending}
              onClick={handleReprocessConfirm}
            >
              {reprocessMutation.isPending ? "Reprocessing…" : "Confirm Reprocess"}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};
