import React, { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/stores/authStore";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { createLogger } from "@/lib/logger";
import type { FingerprintCandidate, ReplacePanelProps } from "./types";

const logger = createLogger("component:FingerprintLookupPanel");

export const FingerprintLookupPanel: React.FC<ReplacePanelProps> = ({
  song,
  onDone,
}) => {
  const { token } = useAuthStore();
  const queryClient = useQueryClient();
  const [candidates, setCandidates] = useState<FingerprintCandidate[] | null>(null);
  const [selected, setSelected] = useState<FingerprintCandidate | null>(null);

  const lookupMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(`/api/songs/${song.id}/fingerprint/lookup`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail ?? "Fingerprint lookup failed");
      }
      return res.json() as Promise<{ candidates: FingerprintCandidate[] }>;
    },
    onSuccess: (data) => {
      setCandidates(data.candidates);
      logger.info("fingerprint lookup: %d candidates for song %s", data.candidates.length, song.id);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  React.useEffect(() => {
    lookupMutation.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const applyMutation = useMutation({
    mutationFn: async (candidate: FingerprintCandidate) => {
      const res = await fetch(`/api/songs/${song.id}/fingerprint/apply`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          recording_id: candidate.recordingId,
          title: candidate.title,
          artist: candidate.artist,
          score: candidate.score,
        }),
      });
      if (!res.ok) throw new Error("Failed to apply candidate");
      return res.json();
    },
    onSuccess: (_data, candidate) => {
      toast.success(`Applied: "${candidate.title}" by ${candidate.artist}`);
      queryClient.invalidateQueries({ queryKey: ["admin-acoustid-songs"] });
      onDone();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="space-y-3">
      {candidates === null ? (
        <p className="text-sm text-muted-foreground">
          {lookupMutation.isPending ? "Running fingerprint lookup..." : "Starting lookup..."}
        </p>
      ) : candidates.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No AcoustID matches found for this audio.
        </p>
      ) : (
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">
            {candidates.length} candidate{candidates.length !== 1 ? "s" : ""} found — click to select
          </p>
          <div className="space-y-1 max-h-64 overflow-y-auto">
            {candidates.map((c) => (
              <div
                key={c.recordingId}
                onClick={() => setSelected(c)}
                className={`flex items-center gap-3 p-2 rounded cursor-pointer transition-colors ${
                  selected?.recordingId === c.recordingId
                    ? "bg-primary/20 border border-primary/40"
                    : "hover:bg-muted/50 border border-transparent"
                }`}
              >
                <div className="shrink-0 flex flex-col items-center w-12">
                  <span
                    className={`text-xs font-mono font-semibold ${
                      c.score >= 0.85
                        ? "text-green-500"
                        : c.score >= 0.5
                          ? "text-amber-500"
                          : "text-red-500"
                    }`}
                  >
                    {Math.round(c.score * 100)}%
                  </span>
                  <span className="text-[10px] text-muted-foreground/60 leading-tight">match</span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">
                    <span className="text-muted-foreground font-normal">Title: </span>
                    {c.title}
                  </p>
                  <p className="text-xs text-muted-foreground truncate">
                    <span className="font-medium text-muted-foreground/60">Artist: </span>
                    {c.artist}
                  </p>
                  <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-0.5">
                    {c.album && (
                      <p className="text-xs text-muted-foreground/70 truncate">
                        <span className="font-medium">Album: </span>{c.album}
                      </p>
                    )}
                    {c.year && (
                      <p className="text-xs text-muted-foreground/70">
                        <span className="font-medium">Year: </span>{c.year}
                      </p>
                    )}
                    {c.releaseType && (
                      <p className="text-xs text-muted-foreground/70">
                        <span className="font-medium">Type: </span>{c.releaseType}
                      </p>
                    )}
                    {c.duration != null && (
                      <p className="text-xs text-muted-foreground/70">
                        <span className="font-medium">Duration: </span>
                        {Math.floor(c.duration / 60)}:{String(Math.round(c.duration % 60)).padStart(2, "0")}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
          {selected && (
            <Button
              size="sm"
              disabled={applyMutation.isPending}
              onClick={() => applyMutation.mutate(selected)}
            >
              {applyMutation.isPending ? "Applying..." : `Apply "${selected.title}"`}
            </Button>
          )}
        </div>
      )}
    </div>
  );
};
