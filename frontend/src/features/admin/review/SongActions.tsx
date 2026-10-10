import React, { useState } from "react";
import { FileText, Search, Trash2 } from "lucide-react";
import { toast } from "sonner";
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
import { Button } from "@/components/ui/button";
import { useApiMutation } from "@/hooks/api/useApi";
import { useSongs } from "@/hooks/api/useSongs";
import LyricsFetchDialog, {
  type LyricsResult,
} from "@/features/lyrics/components/LyricsFetchDialog";
import { PasteLyricsDialog } from "@/features/lyrics/components/PasteLyricsDialog";
import { EditMetadataPanel } from "@/features/songs/components/admin/panels/EditMetadataPanel";
import { FingerprintLookupPanel } from "@/features/songs/components/admin/panels/FingerprintLookupPanel";
import { MusicBrainzSearchPanel } from "@/features/songs/components/admin/panels/MusicBrainzSearchPanel";
import { UploadReplacePanel } from "@/features/songs/components/admin/panels/UploadReplacePanel";
import { YouTubeMusicReplacePanel } from "@/features/songs/components/admin/panels/YouTubeMusicReplacePanel";
import type { Song } from "@/types/Song";
import type { SongBasics } from "./SongPanel";

export type FixPanel =
  | "fingerprint"
  | "musicbrainz"
  | "edit"
  | "replace-yt"
  | "replace-upload";

const PANEL_LABEL: Record<FixPanel, string> = {
  fingerprint: "Look up fingerprint",
  musicbrainz: "Search MusicBrainz",
  edit: "Edit details",
  "replace-yt": "Replace from YouTube Music",
  "replace-upload": "Upload an MP3",
};

/**
 * Buttons that each open a fix below them, one at a time. `open` starts with
 * one already showing.
 */
export const FixPanels: React.FC<{
  song: Song;
  panels: FixPanel[];
  open?: FixPanel;
  onDone: () => void;
  /** More buttons for the same row. */
  children?: React.ReactNode;
}> = ({ song, panels, open, onDone, children }) => {
  const [active, setActive] = useState<FixPanel | null>(open ?? null);
  if (!panels.length && !children) return null;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {panels.map((panel) => (
          <Button
            key={panel}
            size="sm"
            variant={active === panel ? "default" : "outline"}
            aria-expanded={active === panel}
            onClick={() =>
              setActive((current) => (current === panel ? null : panel))
            }
          >
            {PANEL_LABEL[panel]}
          </Button>
        ))}
        {children}
      </div>

      {active === "fingerprint" && (
        <FingerprintLookupPanel song={song} onDone={onDone} />
      )}
      {active === "musicbrainz" && (
        <MusicBrainzSearchPanel song={song} onDone={onDone} />
      )}
      {active === "edit" && <EditMetadataPanel song={song} onDone={onDone} />}
      {active === "replace-yt" && (
        <YouTubeMusicReplacePanel song={song} onDone={onDone} />
      )}
      {active === "replace-upload" && (
        <UploadReplacePanel song={song} onDone={onDone} />
      )}
    </div>
  );
};

/** Delete the song and its files, after a confirm. */
export const DeleteSongButton: React.FC<{
  song: SongBasics;
  onDeleted: () => void;
  label?: string;
}> = ({ song, onDeleted, label = "Delete song" }) => {
  const { useDeleteSong } = useSongs();
  const deleteSong = useDeleteSong();

  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button size="sm" variant="destructive" disabled={deleteSong.isPending}>
          <Trash2 className="mr-1.5 h-3.5 w-3.5" />
          {deleteSong.isPending ? "Deleting…" : label}
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete this song?</AlertDialogTitle>
          <AlertDialogDescription>
            &ldquo;{song.title}&rdquo; and all its audio files go for good.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            onClick={() =>
              deleteSong.mutate(
                { id: song.id },
                {
                  onSuccess: () => {
                    toast.success("Song deleted");
                    onDeleted();
                  },
                  onError: (error) => toast.error(error.message),
                },
              )
            }
          >
            Delete
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
};

/** AcoustID only: keep the song's title and artist as they are, for good. */
export const SkipFingerprintButton: React.FC<{
  songId: string;
  onSkipped: () => void;
}> = ({ songId, onSkipped }) => {
  const skip = useApiMutation<unknown, void>(
    `songs/${songId}/skip-fingerprint`,
    "post",
    {
      onSuccess: () => {
        toast.success("Kept the current title and artist");
        onSkipped();
      },
      onError: (error) => toast.error(error.message),
    },
  );

  return (
    <Button
      size="sm"
      variant="secondary"
      disabled={skip.isPending}
      onClick={() => skip.mutate()}
      title="These details are right. AcoustID won't change or suggest others."
    >
      {skip.isPending ? "Keeping…" : "Keep current details"}
    </Button>
  );
};

/** AcoustID only: rename the song as AcoustID suggested. */
export const AcceptSuggestionButton: React.FC<{
  songId: string;
  onAccepted: () => void;
}> = ({ songId, onAccepted }) => {
  const accept = useApiMutation<unknown, void>(
    `songs/${songId}/fingerprint/suggestion/accept`,
    "post",
    {
      onSuccess: () => {
        toast.success("Renamed to AcoustID's suggestion");
        onAccepted();
      },
      onError: (error) => toast.error(error.message),
    },
  );

  return (
    <Button
      size="sm"
      disabled={accept.isPending}
      onClick={() => accept.mutate()}
    >
      {accept.isPending ? "Renaming…" : "Use suggestion"}
    </Button>
  );
};

/** Measure the singer's lowest and highest notes now. */
export const AnalyzeVocalRangeButton: React.FC<{
  songId: string;
  onDone: () => void;
}> = ({ songId, onDone }) => {
  const analyze = useApiMutation<
    { vocal_range_low: string; vocal_range_high: string },
    void
  >(`songs/${songId}/analyze-vocal-range`, "post", {
    onSuccess: (data) => {
      toast.success(
        `Vocal range: ${data.vocal_range_low} – ${data.vocal_range_high}`,
      );
      onDone();
    },
    onError: (error) => toast.error(error.message),
  });

  return (
    <Button
      size="sm"
      variant="outline"
      disabled={analyze.isPending}
      onClick={() => analyze.mutate()}
    >
      {analyze.isPending ? "Measuring…" : "Measure vocal range"}
    </Button>
  );
};

/** Find other lyrics, or paste some in. `onSaved` runs once they're saved. */
export const LyricsFixButtons: React.FC<{
  song: Song;
  onSaved: () => void;
}> = ({ song, onSaved }) => {
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isPasteOpen, setIsPasteOpen] = useState(false);
  const { useUpdateSong } = useSongs();
  const updateSong = useUpdateSong();

  const save = (
    lyrics: Pick<Song, "plainLyrics" | "syncedLyrics">,
    close: () => void,
  ) =>
    updateSong.mutate(
      { id: song.id, ...lyrics },
      {
        onSuccess: () => {
          close();
          toast.success("Lyrics saved");
          onSaved();
        },
        onError: (error: Error) => toast.error(error.message),
      },
    );

  return (
    <>
      <Button size="sm" variant="outline" onClick={() => setIsSearchOpen(true)}>
        <Search className="mr-1.5 h-3.5 w-3.5" />
        Find other lyrics
      </Button>
      <Button size="sm" variant="outline" onClick={() => setIsPasteOpen(true)}>
        <FileText className="mr-1.5 h-3.5 w-3.5" />
        Paste lyrics
      </Button>

      <LyricsFetchDialog
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        song={song}
        onLyricsSelected={(result: LyricsResult) =>
          save(
            {
              plainLyrics: result.plainLyrics,
              syncedLyrics: result.syncedLyrics,
            },
            () => setIsSearchOpen(false),
          )
        }
      />
      <PasteLyricsDialog
        isOpen={isPasteOpen}
        onClose={() => setIsPasteOpen(false)}
        onLyricsConfirmed={(pasted: string) =>
          save({ plainLyrics: pasted, syncedLyrics: undefined }, () =>
            setIsPasteOpen(false),
          )
        }
      />
    </>
  );
};
