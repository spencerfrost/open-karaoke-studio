import React, { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/stores/authStore";
import { Button } from "@/components/ui/button";
import { Search, FileText } from "lucide-react";
import { useSongs } from "@/hooks/api/useSongs";
import LyricsFetchDialog, {
  type LyricsResult,
} from "@/features/lyrics/components/LyricsFetchDialog";
import { PasteLyricsDialog } from "@/features/lyrics/components/PasteLyricsDialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { toast } from "sonner";
import { Song } from "@/types/Song";
import { SongAudioPreview } from "@/features/songs/components/song-card/SongAudioPreview";
import { EditMetadataPanel } from "./panels/EditMetadataPanel";
import { FingerprintLookupPanel } from "./panels/FingerprintLookupPanel";
import { MusicBrainzSearchPanel } from "./panels/MusicBrainzSearchPanel";
import { YouTubeMusicReplacePanel } from "./panels/YouTubeMusicReplacePanel";
import { UploadReplacePanel } from "./panels/UploadReplacePanel";

type ActiveAction =
  | "edit"
  | "fingerprint"
  | "musicbrainz"
  | "replace-yt"
  | "replace-upload"
  | null;

// Maps data-quality issue types to the button keys that can resolve them.
const ISSUE_ACTION_MAP: Record<string, string[]> = {
  empty_title:         ["edit"],
  empty_artist:        ["edit"],
  suspicious_title:    ["edit", "musicbrainz", "replace-yt"],
  long_title:          ["edit"],
  swapped_fields:      ["edit"],
  encoding_artifact:   ["edit"],
  unknown_artist:      ["edit", "musicbrainz"],
  missing_source:      ["replace-yt", "replace-upload"],
  missing_duration:    ["replace-yt", "replace-upload"],
  missing_album:       ["edit", "musicbrainz"],
  missing_lyrics:      ["search-lyrics", "paste-lyrics"],
  missing_vocal_range: ["analyze-vocal-range"],
};

interface SongActionPanelProps {
  song: Song;
  onDone: () => void;
  /** When provided, only actions relevant to these issue types are shown. */
  issues?: string[];
}

export const SongActionPanel: React.FC<SongActionPanelProps> = ({
  song,
  onDone,
  issues,
}) => {
  const { token } = useAuthStore();
  const queryClient = useQueryClient();
  const [activeAction, setActiveAction] = useState<ActiveAction>(null);

  // When issues are provided, only show actions that can resolve them.
  const allowedActions = issues
    ? new Set(issues.flatMap((t) => ISSUE_ACTION_MAP[t] ?? []))
    : null;
  const show = (action: string) =>
    !allowedActions || allowedActions.has(action);

  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isPasteOpen, setIsPasteOpen] = useState(false);

  const { useUpdateSong } = useSongs();
  const updateSongMutation = useUpdateSong();

  const invalidateAndDone = () => {
    queryClient.invalidateQueries({ queryKey: ["admin-acoustid-songs"] });
    onDone();
  };

  const toggle = (action: ActiveAction) => {
    setActiveAction((prev) => (prev === action ? null : action));
  };

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
      invalidateAndDone();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const handleLyricsSelected = (result: LyricsResult) => {
    updateSongMutation.mutate(
      { id: song.id, plainLyrics: result.plainLyrics, syncedLyrics: result.syncedLyrics },
      {
        onSuccess: () => { setIsSearchOpen(false); invalidateAndDone(); },
        onError: (e: Error) => toast.error(e.message),
      },
    );
  };

  const handlePasteConfirmed = (pastedLyrics: string) => {
    updateSongMutation.mutate(
      { id: song.id, plainLyrics: pastedLyrics, syncedLyrics: undefined },
      {
        onSuccess: () => { setIsPasteOpen(false); invalidateAndDone(); },
        onError: (e: Error) => toast.error(e.message),
      },
    );
  };

  const deleteMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(`/api/songs/${song.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail ?? "Failed to delete song");
      }
    },
    onSuccess: () => {
      toast.success("Song deleted");
      queryClient.invalidateQueries({ queryKey: ["admin-acoustid-songs"] });
      queryClient.invalidateQueries({ queryKey: ["songs"] });
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
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail ?? "Failed to skip song");
      }
    },
    onSuccess: () => {
      toast.success("Song skipped");
      queryClient.invalidateQueries({ queryKey: ["admin-acoustid-songs"] });
      onDone();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="space-y-4">
      {/* Action buttons */}
      <div className="flex flex-wrap gap-2">
        {show("fingerprint") && (
          <Button
            size="sm"
            variant={activeAction === "fingerprint" ? "default" : "outline"}
            onClick={() => toggle("fingerprint")}
          >
            Lookup Fingerprint
          </Button>
        )}
        {show("musicbrainz") && (
          <Button
            size="sm"
            variant={activeAction === "musicbrainz" ? "default" : "outline"}
            onClick={() => toggle("musicbrainz")}
          >
            Search MusicBrainz
          </Button>
        )}
        {show("edit") && (
          <Button
            size="sm"
            variant={activeAction === "edit" ? "default" : "outline"}
            onClick={() => toggle("edit")}
          >
            Edit Metadata
          </Button>
        )}
        {show("analyze-vocal-range") && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => analyzeVocalRangeMutation.mutate()}
            disabled={analyzeVocalRangeMutation.isPending}
          >
            {analyzeVocalRangeMutation.isPending ? "Analyzing..." : "Analyze Vocal Range"}
          </Button>
        )}
        {show("search-lyrics") && (
          <Button size="sm" variant="outline" onClick={() => setIsSearchOpen(true)}>
            <Search className="w-3.5 h-3.5 mr-1.5" />
            Search Lyrics
          </Button>
        )}
        {show("paste-lyrics") && (
          <Button size="sm" variant="outline" onClick={() => setIsPasteOpen(true)}>
            <FileText className="w-3.5 h-3.5 mr-1.5" />
            Paste Lyrics
          </Button>
        )}
        {show("replace-yt") && (
          <Button
            size="sm"
            variant={activeAction === "replace-yt" ? "default" : "outline"}
            onClick={() => toggle("replace-yt")}
          >
            Replace from YouTube Music
          </Button>
        )}
        {show("replace-upload") && (
          <Button
            size="sm"
            variant={activeAction === "replace-upload" ? "default" : "outline"}
            onClick={() => toggle("replace-upload")}
          >
            Upload MP3
          </Button>
        )}
        <Button
          size="sm"
          variant="secondary"
          onClick={() => skipMutation.mutate()}
          disabled={skipMutation.isPending}
        >
          {skipMutation.isPending ? "Skipping..." : "Skip"}
        </Button>
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button size="sm" variant="destructive">
              Delete Song
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete song?</AlertDialogTitle>
              <AlertDialogDescription>
                This will permanently delete &ldquo;{song.title}&rdquo; and all
                associated audio files. This action cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={() => deleteMutation.mutate()}
                disabled={deleteMutation.isPending}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                {deleteMutation.isPending ? "Deleting..." : "Delete"}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>

      {/* Edit metadata panel */}
      {activeAction === "edit" && (
        <EditMetadataPanel song={song} onDone={invalidateAndDone} />
      )}

      {/* Fingerprint lookup panel */}
      {activeAction === "fingerprint" && (
        <FingerprintLookupPanel song={song} onDone={invalidateAndDone} />
      )}

      {/* MusicBrainz search panel */}
      {activeAction === "musicbrainz" && (
        <MusicBrainzSearchPanel song={song} onDone={invalidateAndDone} />
      )}

      {/* YouTube Music replace panel */}
      {activeAction === "replace-yt" && (
        <YouTubeMusicReplacePanel song={song} onDone={invalidateAndDone} />
      )}

      {/* Upload replace panel */}
      {activeAction === "replace-upload" && (
        <UploadReplacePanel song={song} onDone={invalidateAndDone} />
      )}

      <LyricsFetchDialog
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        song={song}
        onLyricsSelected={handleLyricsSelected}
      />
      <PasteLyricsDialog
        isOpen={isPasteOpen}
        onClose={() => setIsPasteOpen(false)}
        onLyricsConfirmed={handlePasteConfirmed}
      />

      {/* Audio preview — always visible */}
      <div className="pt-1 border-t">
        <SongAudioPreview songId={song.id} />
      </div>
    </div>
  );
};
