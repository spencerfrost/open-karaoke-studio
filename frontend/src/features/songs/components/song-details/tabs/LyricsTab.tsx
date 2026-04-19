import React, { useState, useCallback } from "react";
import { Song } from "@/types/Song";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useSongs } from "@/hooks/api/useSongs";
import { toast } from "sonner";
import { createLogger } from "@/lib/logger";
import LyricsFetchDialog from "@/features/lyrics/components/LyricsFetchDialog";
import PasteLyricsDialog from "@/features/lyrics/components/PasteLyricsDialog";
import type { LyricsResult } from "@/features/lyrics/components/LyricsFetchDialog";

const logger = createLogger("component:LyricsTab");

interface LyricsTabProps {
  song: Song;
}

export const LyricsTab: React.FC<LyricsTabProps> = ({ song }) => {
  const { useUpdateSong } = useSongs();
  const updateSongMutation = useUpdateSong();

  const [isEditingPlain, setIsEditingPlain] = useState(false);
  const [plainEditValue, setPlainEditValue] = useState(song.plainLyrics ?? "");

  const [isEditingSynced, setIsEditingSynced] = useState(false);
  const [syncedEditValue, setSyncedEditValue] = useState(
    song.syncedLyrics ?? "",
  );

  const [isPlainFetchDialogOpen, setIsPlainFetchDialogOpen] = useState(false);
  const [isSyncedFetchDialogOpen, setIsSyncedFetchDialogOpen] = useState(false);
  const [isPasteDialogOpen, setIsPasteDialogOpen] = useState(false);
  const [pasteTarget, setPasteTarget] = useState<"plain" | "synced">("plain");

  const handlePlainLyricsSelected = useCallback(
    (result: LyricsResult) => {
      updateSongMutation.mutate(
        { id: song.id, plainLyrics: result.plainLyrics },
        {
          onSuccess: () => {
            setIsPlainFetchDialogOpen(false);
            toast.success("Plain lyrics updated");
          },
          onError: (error) => {
            logger.error("Failed to update plain lyrics", error);
            toast.error(
              `Failed to update lyrics: ${error instanceof Error ? error.message : "Unknown error"}`,
            );
          },
        },
      );
    },
    [song.id, updateSongMutation],
  );

  const handleSyncedLyricsSelected = useCallback(
    (result: LyricsResult) => {
      updateSongMutation.mutate(
        { id: song.id, syncedLyrics: result.syncedLyrics },
        {
          onSuccess: () => {
            setIsSyncedFetchDialogOpen(false);
            toast.success("Synced lyrics updated");
          },
          onError: (error) => {
            logger.error("Failed to update synced lyrics", error);
            toast.error(
              `Failed to update lyrics: ${error instanceof Error ? error.message : "Unknown error"}`,
            );
          },
        },
      );
    },
    [song.id, updateSongMutation],
  );

  const handlePasteConfirmed = useCallback(
    (pasted: string) => {
      const patch =
        pasteTarget === "plain"
          ? { id: song.id, plainLyrics: pasted }
          : { id: song.id, syncedLyrics: pasted };

      updateSongMutation.mutate(patch, {
        onSuccess: () => {
          setIsPasteDialogOpen(false);
          toast.success("Lyrics pasted successfully");
        },
        onError: (error) => {
          logger.error("Failed to paste lyrics", error);
          toast.error(
            `Failed to save lyrics: ${error instanceof Error ? error.message : "Unknown error"}`,
          );
        },
      });
    },
    [song.id, pasteTarget, updateSongMutation],
  );

  const savePlain = useCallback(() => {
    updateSongMutation.mutate(
      { id: song.id, plainLyrics: plainEditValue },
      {
        onSuccess: () => {
          setIsEditingPlain(false);
          toast.success("Plain lyrics saved");
        },
        onError: (error) => {
          logger.error("Failed to save plain lyrics", error);
          toast.error(
            `Failed to save: ${error instanceof Error ? error.message : "Unknown error"}`,
          );
        },
      },
    );
  }, [song.id, plainEditValue, updateSongMutation]);

  const saveSynced = useCallback(() => {
    updateSongMutation.mutate(
      { id: song.id, syncedLyrics: syncedEditValue },
      {
        onSuccess: () => {
          setIsEditingSynced(false);
          toast.success("Synced lyrics saved");
        },
        onError: (error) => {
          logger.error("Failed to save synced lyrics", error);
          toast.error(
            `Failed to save: ${error instanceof Error ? error.message : "Unknown error"}`,
          );
        },
      },
    );
  }, [song.id, syncedEditValue, updateSongMutation]);

  const clearWordSynced = useCallback(() => {
    updateSongMutation.mutate(
      { id: song.id, wordSyncedLyrics: null as unknown as string },
      {
        onSuccess: () => toast.success("Word-synced lyrics cleared"),
        onError: (error) => {
          logger.error("Failed to clear word-synced lyrics", error);
          toast.error(
            `Failed to clear: ${error instanceof Error ? error.message : "Unknown error"}`,
          );
        },
      },
    );
  }, [song.id, updateSongMutation]);

  let wordSyncedDisplay: string | null = null;
  if (song.wordSyncedLyrics) {
    try {
      wordSyncedDisplay = JSON.stringify(
        JSON.parse(song.wordSyncedLyrics),
        null,
        2,
      );
    } catch {
      wordSyncedDisplay = song.wordSyncedLyrics;
    }
  }

  return (
    <>
      <Tabs defaultValue="plain">
        <TabsList className="grid grid-cols-3 w-full">
          <TabsTrigger value="plain">
            Plain{song.plainLyrics ? " ●" : ""}
          </TabsTrigger>
          <TabsTrigger value="synced">
            Synced{song.syncedLyrics ? " ●" : ""}
          </TabsTrigger>
          <TabsTrigger value="word-synced">
            Word-Synced{song.wordSyncedLyrics ? " ●" : ""}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="plain" className="space-y-2 mt-3">
          {isEditingPlain ? (
            <Textarea
              value={plainEditValue}
              onChange={(e) => setPlainEditValue(e.target.value)}
              rows={12}
              autoFocus
            />
          ) : song.plainLyrics ? (
            <div className="max-h-64 overflow-y-auto text-sm whitespace-pre-wrap">
              {song.plainLyrics}
            </div>
          ) : (
            <p className="text-muted-foreground text-sm py-8 text-center">
              No plain lyrics
            </p>
          )}
          <div className="flex gap-2">
            {isEditingPlain ? (
              <>
                <Button
                  size="sm"
                  onClick={savePlain}
                  disabled={updateSongMutation.isPending}
                >
                  Save
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setPlainEditValue(song.plainLyrics ?? "");
                    setIsEditingPlain(false);
                  }}
                >
                  Cancel
                </Button>
              </>
            ) : (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsPlainFetchDialogOpen(true)}
                >
                  Search
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setPasteTarget("plain");
                    setIsPasteDialogOpen(true);
                  }}
                >
                  Paste
                </Button>
                {song.plainLyrics && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setPlainEditValue(song.plainLyrics ?? "");
                      setIsEditingPlain(true);
                    }}
                  >
                    Edit
                  </Button>
                )}
              </>
            )}
          </div>
        </TabsContent>

        <TabsContent value="synced" className="space-y-2 mt-3">
          {isEditingSynced ? (
            <Textarea
              value={syncedEditValue}
              onChange={(e) => setSyncedEditValue(e.target.value)}
              rows={12}
              autoFocus
            />
          ) : song.syncedLyrics ? (
            <div className="max-h-64 overflow-y-auto text-sm whitespace-pre-wrap">
              {song.syncedLyrics}
            </div>
          ) : (
            <p className="text-muted-foreground text-sm py-8 text-center">
              No synced lyrics
            </p>
          )}
          <div className="flex gap-2">
            {isEditingSynced ? (
              <>
                <Button
                  size="sm"
                  onClick={saveSynced}
                  disabled={updateSongMutation.isPending}
                >
                  Save
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setSyncedEditValue(song.syncedLyrics ?? "");
                    setIsEditingSynced(false);
                  }}
                >
                  Cancel
                </Button>
              </>
            ) : (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsSyncedFetchDialogOpen(true)}
                >
                  Search
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setPasteTarget("synced");
                    setIsPasteDialogOpen(true);
                  }}
                >
                  Paste
                </Button>
                {song.syncedLyrics && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setSyncedEditValue(song.syncedLyrics ?? "");
                      setIsEditingSynced(true);
                    }}
                  >
                    Edit
                  </Button>
                )}
              </>
            )}
          </div>
        </TabsContent>

        <TabsContent value="word-synced" className="space-y-2 mt-3">
          {wordSyncedDisplay ? (
            <pre className="max-h-64 overflow-y-auto text-xs bg-muted rounded p-3 whitespace-pre-wrap">
              {wordSyncedDisplay}
            </pre>
          ) : (
            <p className="text-muted-foreground text-sm py-8 text-center">
              No word-synced lyrics
            </p>
          )}
          {song.wordSyncedLyrics && (
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={clearWordSynced}
                disabled={updateSongMutation.isPending}
              >
                Clear
              </Button>
            </div>
          )}
        </TabsContent>
      </Tabs>

      <LyricsFetchDialog
        isOpen={isPlainFetchDialogOpen}
        onClose={() => setIsPlainFetchDialogOpen(false)}
        song={song}
        onLyricsSelected={handlePlainLyricsSelected}
      />
      <LyricsFetchDialog
        isOpen={isSyncedFetchDialogOpen}
        onClose={() => setIsSyncedFetchDialogOpen(false)}
        song={song}
        onLyricsSelected={handleSyncedLyricsSelected}
      />
      <PasteLyricsDialog
        isOpen={isPasteDialogOpen}
        onClose={() => setIsPasteDialogOpen(false)}
        onLyricsConfirmed={handlePasteConfirmed}
      />
    </>
  );
};
