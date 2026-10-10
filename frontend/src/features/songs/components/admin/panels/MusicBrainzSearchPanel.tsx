import React, { useState } from "react";
import { useApiQuery } from "@/hooks/api/useApi";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { MusicBrainzResult, ReplacePanelProps } from "./types";
import { useApplyRecording } from "./useApplyRecording";

export const MusicBrainzSearchPanel: React.FC<ReplacePanelProps> = ({
  song,
  onDone,
}) => {
  const initialQuery = [
    song.title && `recording:"${song.title}"`,
    song.artist && `artist:"${song.artist}"`,
  ]
    .filter(Boolean)
    .join(" AND ");
  const [query, setQuery] = useState(initialQuery);
  const [debouncedQuery, setDebouncedQuery] = useState(initialQuery);
  const [selected, setSelected] = useState<MusicBrainzResult | null>(null);

  const timeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const handleQueryChange = (value: string) => {
    setQuery(value);
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => setDebouncedQuery(value), 400);
  };

  const { data, isFetching } = useApiQuery<
    { results: MusicBrainzResult[] },
    readonly [string, string]
  >(
    ["musicbrainz-search", debouncedQuery] as const,
    `musicbrainz/search?query=${encodeURIComponent(debouncedQuery)}&limit=15`,
    { enabled: !!debouncedQuery, staleTime: 60_000 },
  );

  const applyMutation = useApplyRecording(song.id, onDone);

  const results = data?.results ?? [];

  return (
    <div className="space-y-3">
      <Input
        value={query}
        onChange={(e) => handleQueryChange(e.target.value)}
        placeholder="Search MusicBrainz..."
        className="h-8 text-sm"
      />

      {isFetching && (
        <p className="text-xs text-muted-foreground">Searching...</p>
      )}

      {results.length > 0 && (
        <div className="space-y-1 max-h-64 overflow-y-auto">
          {results.map((r) => (
            <div
              key={r.recordingId}
              onClick={() => setSelected(r)}
              className={`flex items-center gap-3 p-2 rounded cursor-pointer transition-colors ${
                selected?.recordingId === r.recordingId
                  ? "bg-primary/20 border border-primary/40"
                  : "hover:bg-muted/50 border border-transparent"
              }`}
            >
              <span
                className={`text-xs font-mono font-semibold shrink-0 w-10 text-right ${
                  r.score >= 0.85
                    ? "text-success-strong"
                    : r.score >= 0.5
                      ? "text-warning-strong"
                      : "text-destructive-strong"
                }`}
              >
                {Math.round(r.score * 100)}%
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{r.title}</p>
                <p className="text-xs text-muted-foreground truncate">
                  {r.artist}
                  {r.album ? ` · ${r.album}` : ""}
                  {r.releaseDate ? ` (${r.releaseDate.slice(0, 4)})` : ""}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      {selected && (
        <Button
          size="sm"
          disabled={applyMutation.isPending}
          onClick={() => applyMutation.mutate(selected)}
        >
          {applyMutation.isPending
            ? "Applying..."
            : `Apply "${selected.title}"`}
        </Button>
      )}
    </div>
  );
};
