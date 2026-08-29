import React, { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { apiSend } from "@/hooks/api/useApi";
import { useYoutubeMusicSearch } from "@/hooks/api/useYoutubeMusic";
import { useSongRecovery } from "@/features/songs/hooks/useSongRecovery";
import { YoutubeMusicSearchResult } from "@/types/Youtube";
import type { ReplacePanelProps, ValidationResult } from "./types";

export const YouTubeMusicReplacePanel: React.FC<ReplacePanelProps> = ({
  song,
  onDone,
}) => {
  const [query, setQuery] = useState(`${song.artist} ${song.title}`);
  const [debouncedQuery, setDebouncedQuery] = useState(query);
  const [selected, setSelected] = useState<YoutubeMusicSearchResult | null>(
    null,
  );
  const [validation, setValidation] = useState<ValidationResult | null>(null);

  // Simple debounce via timeout ref
  const timeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const handleQueryChange = (value: string) => {
    setQuery(value);
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => setDebouncedQuery(value), 400);
  };

  const { data, isFetching } = useYoutubeMusicSearch(
    debouncedQuery,
    !!debouncedQuery,
  );
  const songs = data?.songs ?? [];

  const validateMutation = useMutation({
    mutationFn: (result: YoutubeMusicSearchResult) =>
      apiSend<ValidationResult, Record<string, unknown>>(
        `songs/${song.id}/validate-youtube-replacement`,
        "post",
        {
          video_id: result.videoId,
          title: result.title,
          artist: result.artist,
          engine_type: "three_track",
        },
      ),
    onSuccess: (result) => setValidation(result),
    onError: (e: Error) => toast.error(e.message),
  });

  // Same /replace-youtube dispatch the library-audit and song-detail retries
  // use, so the request shape and error handling stay in one place.
  const { recoverSong, isRecovering } = useSongRecovery({
    onSuccess: () => onDone(),
  });
  const isReplacing = isRecovering(song.id);

  const handleSelect = (result: YoutubeMusicSearchResult) => {
    setSelected(result);
    setValidation(null);
    validateMutation.mutate(result);
  };

  return (
    <div className="space-y-3">
      <Input
        value={query}
        onChange={(e) => handleQueryChange(e.target.value)}
        placeholder="Search YouTube Music..."
        className="h-8 text-sm"
      />

      {isFetching && (
        <p className="text-xs text-muted-foreground">Searching...</p>
      )}

      {songs.length > 0 && (
        <div className="space-y-1 max-h-48 overflow-y-auto">
          {songs.map((result) => (
            <div
              key={result.videoId}
              onClick={() => handleSelect(result)}
              className={`flex items-center gap-3 p-2 rounded cursor-pointer transition-colors ${
                selected?.videoId === result.videoId
                  ? "bg-primary/20 border border-primary/40"
                  : "hover:bg-muted/50 border border-transparent"
              }`}
            >
              {result.thumbnails[0] && (
                <img
                  src={result.thumbnails[0].url}
                  alt=""
                  className="w-8 h-8 rounded object-cover shrink-0"
                />
              )}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{result.title}</p>
                <p className="text-xs text-muted-foreground truncate">
                  {result.artist}
                  {result.duration ? ` · ${result.duration}` : ""}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      {validateMutation.isPending && (
        <p className="text-xs text-muted-foreground">Checking AcoustID...</p>
      )}

      {validation && (
        <div
          className={`rounded border p-3 text-sm space-y-2 ${
            validation.validated
              ? "bg-success/10 border-success/40"
              : "bg-warning/10 border-warning/40"
          }`}
        >
          <p
            className={
              validation.validated
                ? "text-success-strong"
                : "text-warning-strong"
            }
          >
            {validation.message}
          </p>
          {validation.acoustidStatus === "matched" && validation.title && (
            <p className="text-xs text-muted-foreground">
              Matched:{" "}
              <span className="text-card-foreground">{validation.title}</span>
              {" by "}
              <span className="text-card-foreground">{validation.artist}</span>
            </p>
          )}
          <div className="flex gap-2 pt-1">
            {validation.validated ? (
              <Button
                size="sm"
                disabled={isReplacing}
                onClick={() =>
                  recoverSong({
                    id: song.id,
                    title: selected!.title,
                    artist: selected!.artist,
                    videoId: selected!.videoId,
                  })
                }
              >
                {isReplacing ? "Starting..." : "Confirm & Process"}
              </Button>
            ) : (
              <p className="text-xs text-muted-foreground italic">
                Try a different track, or use MusicBrainz to set metadata
                manually.
              </p>
            )}
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setValidation(null);
                setSelected(null);
              }}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};
