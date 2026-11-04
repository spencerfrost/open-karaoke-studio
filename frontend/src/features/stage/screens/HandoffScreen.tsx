/**
 * HandoffScreen - the gap between songs, and the only moment the rotation is
 * load-bearing.
 *
 * This replaces SongEnded and QueueEnded, which were chosen by a length check on
 * the queue and shared no layout, no hierarchy and no concept of a person. The
 * merge is not cosmetic: once ordering comes from a roster, **"the queue is
 * empty" stops being a state.** It collapses into one reading of the question
 * this screen always asks - *whose turn is it, and do they have a song?* An
 * empty queue is not a conclusion, it is Sarah's turn with nothing in her slot.
 *
 * Turn logic built into two sibling components gets implemented twice and
 * drifts, the way the two queue serializers already did. One screen, one state
 * machine, and the machine itself lives on the server: this renders
 * `queue.turn`, it never decides it.
 *
 * Three slots, always in the same place:
 *   1. Who's up      - the name, at headline scale.
 *   2. What they're singing - the only slot whose content varies.
 *   3. How to change either - Skip my turn, Add performer, Remove from
 *      rotation. Quiet, always present, never a modal.
 *
 * The rotation is authoritative: nobody overrules whose turn it is from here.
 * Someone who walks up out of turn is added at the turn instead, and keeps
 * that seat for the night.
 *
 * No clock runs here. This is a living-room app: the screen waits until
 * someone taps, rather than playing the next song or passing over a person who
 * hasn't picked one yet.
 */

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  BookOpen,
  Music,
  Play,
  SkipForward,
  UserMinus,
  UserPlus,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { QRCodeDisplay } from "@/features/queue";
import { useSongs } from "@/hooks/api/useSongs";
import { useAddToKaraokeQueue } from "@/hooks/api/useKaraokeQueue";
import {
  useInsertPerformer,
  useRemovePerformer,
  useRestorePerformer,
  useSkipTurn,
  TurnMovedOnError,
} from "@/hooks/api/useTurn";
import { useSessionStore } from "@/stores/sessionStore";
import { createLogger } from "@/lib/logger";
import { cn } from "@/lib/utils";
import type {
  KaraokeQueueItemWithSong,
  SessionTurn,
} from "@/types/KaraokeQueue";
import type { SessionPerformer } from "@/types/SessionPerformer";
import type { Song } from "@/types/Song";
import {
  useSongSuggestions,
  getSuggestionReasonText,
} from "@/features/player/hooks/useSongSuggestions";
import LyricsFeedbackRow from "../components/LyricsFeedbackRow";
import { useStageShell } from "../StageShellContext";
import { findTurnItem } from "../turnItem";

const logger = createLogger("component:handoff-screen");

interface HandoffScreenProps {
  /** The song that just finished, or null if nothing was playing. */
  current?: KaraokeQueueItemWithSong | null;
  upcoming: KaraokeQueueItemWithSong[];
  turn: SessionTurn;
  roster: SessionPerformer[];
  /** Start a queue item playing - the same handler the queue rail uses. */
  onPlayFromQueue: (id: string) => void;
}

const HandoffScreen: React.FC<HandoffScreenProps> = ({
  current,
  upcoming,
  turn,
  roster,
  onPlayFromQueue,
}) => {
  const shell = useStageShell();
  const { getArtworkUrl } = useSongs();
  const { displayCode } = useSessionStore();

  const sessionCode = displayCode || undefined;
  const skipTurn = useSkipTurn(sessionCode);
  const insertPerformer = useInsertPerformer(sessionCode);
  const removePerformer = useRemovePerformer(sessionCode);
  const restorePerformer = useRestorePerformer(sessionCode);
  const addToQueue = useAddToKaraokeQueue(sessionCode);

  // "Add performer" swaps slot 2 for a name field.
  const [isAdding, setIsAdding] = useState(false);
  const [newName, setNewName] = useState("");

  // Shared with the shell, which uses it to decide whether Back from the
  // library comes here at all.
  const nextItem = findTurnItem(turn, upcoming);
  const hasSong = nextItem !== null;

  // A 409 means somebody else got there first. Both screens are about to be
  // told the same thing by the queue broadcast, so there is nothing to say.
  const onTurnError = useCallback((error: Error, action: string) => {
    if (error instanceof TurnMovedOnError) {
      logger.debug("%s lost the race; the broadcast will settle it", action);
      return;
    }
    logger.error("%s failed:", action, error);
    toast.error(`Couldn't ${action}`, { description: error.message });
  }, []);

  const handleAdvance = useCallback(() => {
    if (nextItem) onPlayFromQueue(nextItem.id);
  }, [nextItem, onPlayFromQueue]);

  const handleSkip = useCallback(() => {
    skipTurn.mutate(
      { expectedPerformerId: turn.performerId },
      { onError: (e) => onTurnError(e, "skip the turn") },
    );
  }, [skipTurn, turn.performerId, onTurnError]);

  const handleInsert = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      const name = newName.trim();
      if (!name) return;
      insertPerformer.mutate(
        { expectedPerformerId: turn.performerId, name },
        {
          onSuccess: () => {
            setIsAdding(false);
            setNewName("");
          },
          onError: (err) => onTurnError(err, `add ${name}`),
        },
      );
    },
    [insertPerformer, newName, turn.performerId, onTurnError],
  );

  // No confirm dialog: the undo toast is the safety net.
  const handleRemove = useCallback(() => {
    const { performerId, performerName } = turn;
    if (performerId === null) return;
    removePerformer.mutate(
      { expectedPerformerId: performerId, performerId },
      {
        onSuccess: (removed) => {
          toast(`${performerName ?? "They"} left the rotation`, {
            duration: 10000,
            action: {
              label: "Undo",
              onClick: () =>
                restorePerformer.mutate(
                  {
                    performerId: removed.id,
                    expectedHolderId: removed.holder_id,
                  },
                  { onError: (e) => onTurnError(e, "undo that") },
                ),
            },
          });
        },
        onError: (e) => onTurnError(e, "remove them"),
      },
    );
  }, [removePerformer, restorePerformer, turn, onTurnError]);

  // Keys, bound on the window like the confirm screen's, so nobody has to
  // reach for the mouse between songs:
  //   Enter      play their song, or open the library when they have none
  //   Back / L   the library
  // While "Add performer" is open, Back means "Never mind" and Enter belongs
  // to its form.
  const keys = useRef({ hasSong, isAdding, handleAdvance });
  keys.current = { hasSong, isAdding, handleAdvance };
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      const t = e.target instanceof HTMLElement ? e.target : null;
      const k = keys.current;
      // The name field is typing, not navigating.
      if (
        t &&
        (["INPUT", "TEXTAREA", "SELECT"].includes(t.tagName) ||
          t.isContentEditable)
      ) {
        if (e.key === "Escape" && k.isAdding) setIsAdding(false);
        return;
      }
      if (t?.closest("[role='dialog'], [role='slider']")) return;

      if (e.key === "Escape" || e.key === "Backspace") {
        e.preventDefault();
        if (e.repeat) return;
        if (k.isAdding) setIsAdding(false);
        else shell?.openSelect();
        return;
      }
      if (k.isAdding) return;

      if (e.code === "KeyL") {
        e.preventDefault();
        if (e.repeat) return;
        shell?.openSelect();
        return;
      }
      if (e.key === "Enter") {
        // A button the mouse just clicked keeps Enter for itself.
        if (t?.closest("button, a, [role='button']")) return;
        e.preventDefault();
        // The Enter that started the last song, still held, must not start
        // this one.
        if (e.repeat) return;
        if (k.hasSong) k.handleAdvance();
        else shell?.openSelect();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [shell]);

  const { suggestions, isLoading: suggestionsLoading } = useSongSuggestions(
    current?.song ? { currentSong: current.song, limit: 4 } : null,
  );

  const handleSuggestion = (song: Song) => {
    // Filed under whoever's turn it is, not the host. QueueEnded used to file
    // every one of these under the literal string "Host".
    const singer = turn.performerName;
    if (!singer) {
      shell?.openConfirm(song);
      return;
    }
    addToQueue.mutate(
      { songId: song.id, singer },
      {
        onSuccess: () => toast.success(`Added "${song.title}" for ${singer}`),
        onError: () => toast.error(`Failed to add "${song.title}"`),
      },
    );
  };

  // The next few *people*, so they can get ready - whose turns come next, not
  // whose songs: someone with three songs queued is still one seat. The circle
  // starts at whoever holds the turn. Leaving out the person on screen covers
  // both the normal case (they are the holder) and a bumped song (the holder
  // is next after them).
  // Append mode has no circle, so there it is the singers of the next songs.
  const onDeck = useMemo(
    () =>
      turn.circle.length > 0
        ? turn.circle
            .filter((p) => p.id !== turn.performerId)
            .slice(0, 3)
            .map((p) => p.name)
        : upcoming
            .filter((item) => Number(item.id) !== turn.itemId)
            .slice(0, 3)
            .map((item) => item.singer),
    [turn.circle, turn.performerId, upcoming, turn.itemId],
  );

  // An audience of one should not be told about a rotation.
  const showRibbon = turn.circle.length >= 2;

  return (
    // Short screens (the Shield's 960x540) get a tighter layout. Centering is
    // "safe": anything that still doesn't fit falls off the bottom, not the top.
    <div className="flex h-full w-full flex-col items-center justify-center-safe gap-10 overflow-auto p-10 [@media(max-height:600px)]:gap-5 [@media(max-height:600px)]:p-6">
      {/* ---- Slot 1: who's up ------------------------------------------- */}
      <div className="text-center">
        {turn.performerName ? (
          <>
            <p className="text-xl uppercase tracking-[0.2em] text-foreground-faint [@media(max-height:600px)]:text-base">
              Up next
            </p>
            <h1 className="font-display text-8xl leading-none text-primary [@media(max-height:600px)]:text-6xl">
              {turn.performerName}
            </h1>
          </>
        ) : (
          <h1 className="font-display text-6xl leading-tight text-foreground">
            Who's singing?
          </h1>
        )}
      </div>

      {/* ---- Slot 2: what they're singing -------------------------------- */}
      <div className="flex w-full max-w-4xl flex-col items-center gap-6">
        {isAdding ? (
          <form
            onSubmit={handleInsert}
            className="w-full max-w-xl space-y-4 text-center"
          >
            <p className="text-xl text-foreground-dim">
              {turn.performerName
                ? `They'll sing now, and ${turn.performerName} goes next.`
                : "They'll sing now."}
            </p>
            <Input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Their name"
              aria-label="Performer name"
              maxLength={100}
              autoFocus
              className="h-14 text-center text-2xl"
            />
            <div className="flex justify-center gap-3 pt-2">
              <Button
                type="button"
                variant="ghost"
                onClick={() => setIsAdding(false)}
              >
                Never mind
              </Button>
              <Button
                type="submit"
                variant="primary"
                size="lg"
                disabled={!newName.trim() || insertPerformer.isPending}
              >
                Add
              </Button>
            </div>
          </form>
        ) : hasSong && nextItem ? (
          <button
            onClick={handleAdvance}
            className="group flex items-center gap-8 rounded-xl p-2 text-left"
            aria-label={`Play ${nextItem.song.title}`}
          >
            <div className="relative flex size-48 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-overlay/60 shadow-2xl [@media(max-height:600px)]:size-32">
              {getArtworkUrl(nextItem.song, "large") ? (
                <img
                  src={getArtworkUrl(nextItem.song, "large") ?? undefined}
                  alt=""
                  className="size-full object-cover transition-transform duration-300 group-hover:scale-105"
                />
              ) : (
                <Music size={64} className="text-foreground-faint" />
              )}
              <div className="absolute inset-0 flex items-center justify-center bg-overlay/40 transition-colors group-hover:bg-overlay/50">
                <Play
                  size={48}
                  className="text-foreground drop-shadow-lg transition-transform group-hover:scale-110"
                  fill="currentColor"
                  strokeWidth={0}
                />
              </div>
            </div>
            <div className="min-w-0">
              <h2 className="font-display text-5xl leading-tight text-foreground [@media(max-height:600px)]:text-4xl">
                {nextItem.song.title}
              </h2>
              <p className="pt-2 text-2xl text-foreground-dim">
                {nextItem.song.artist}
              </p>
            </div>
          </button>
        ) : turn.kind === "open" && roster.length === 0 && displayCode ? (
          <div className="flex flex-col items-center gap-5">
            <p className="text-2xl text-foreground-dim">
              Scan to join and pick a song
            </p>
            <QRCodeDisplay
              value={`${window.location.origin}/join/${displayCode}`}
              size={200}
            />
            <p className="font-accent text-5xl leading-tight text-primary">
              {displayCode}
            </p>
          </div>
        ) : (
          <div className="flex w-full flex-col items-center gap-6">
            <p className="text-2xl text-foreground-dim">
              {turn.performerName
                ? `${turn.performerName} — check your phone, or pick one here`
                : "Pick something to keep it going"}
            </p>

            {suggestions.length > 0 && (
              <div className="w-full">
                <h3 className="pb-3 text-center text-lg text-foreground-faint">
                  {getSuggestionReasonText(suggestions[0].reason)}
                </h3>
                <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                  {suggestions.map(({ song }) => (
                    <button
                      key={song.id}
                      onClick={() => handleSuggestion(song)}
                      className="group overflow-hidden rounded-lg bg-overlay/60 text-left transition-all duration-200 hover:scale-105 hover:bg-overlay/80 hover:ring-2 hover:ring-primary/50"
                    >
                      <div className="relative aspect-video w-full">
                        {getArtworkUrl(song, "medium") ? (
                          <img
                            src={getArtworkUrl(song, "medium") ?? undefined}
                            alt=""
                            className="size-full object-cover"
                          />
                        ) : (
                          <div className="flex size-full items-center justify-center bg-primary/20">
                            <Music
                              size={32}
                              className="text-foreground-faint"
                            />
                          </div>
                        )}
                      </div>
                      <div className="p-2">
                        <p className="truncate text-base font-medium text-foreground">
                          {song.title}
                        </p>
                        <p className="truncate text-sm text-foreground-dim">
                          {song.artist}
                        </p>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {suggestionsLoading && (
              <p className="text-foreground-faint">Finding more songs…</p>
            )}

            <Button
              variant="outline"
              size="lg"
              onClick={() => shell?.openSelect()}
              className="gap-2"
            >
              <BookOpen className="size-5" />
              Open the Songbook
            </Button>
          </div>
        )}
      </div>

      {/* ---- Slot 3: how to change either -------------------------------- */}
      {!isAdding && (
        <div className="flex w-full max-w-4xl flex-col items-center gap-4 [@media(max-height:600px)]:gap-2">
          {/* The circle is empty in append mode, which has no turns to change. */}
          {turn.circle.length > 0 && (
            <div className="flex flex-col items-center gap-2">
              {turn.performerId !== null && (
                <Button
                  variant="outline"
                  size="lg"
                  onClick={handleSkip}
                  disabled={skipTurn.isPending}
                  className="gap-2"
                >
                  <SkipForward className="size-5" />
                  Skip my turn
                </Button>
              )}
              <div className="flex items-center gap-3">
                <Button
                  variant="ghost"
                  size="lg"
                  onClick={() => {
                    setNewName("");
                    setIsAdding(true);
                  }}
                  className="gap-2 text-foreground-dim hover:text-foreground"
                >
                  <UserPlus className="size-5" />
                  Add performer
                </Button>
                {turn.performerId !== null && (
                  <>
                    <span className="text-foreground-faint">·</span>
                    <Button
                      variant="ghost"
                      size="lg"
                      onClick={handleRemove}
                      disabled={removePerformer.isPending}
                      className="gap-2 text-foreground-dim hover:text-foreground"
                    >
                      <UserMinus className="size-5" />
                      Remove from rotation
                    </Button>
                  </>
                )}
              </div>
            </div>
          )}

          {onDeck.length > 0 && (
            <p className="text-lg text-foreground-faint">
              On deck:{" "}
              <span className="text-foreground-dim">{onDeck.join(" · ")}</span>
            </p>
          )}

          {showRibbon && (
            <p
              className={cn(
                "text-base uppercase tracking-[0.15em] text-foreground-faint",
              )}
            >
              {turn.circle.map((p) => p.name).join(" → ")} →{" "}
              {turn.circle[0].name}
            </p>
          )}

          {current?.song && (
            <p className="pt-2 text-sm text-foreground-faint">
              Just played: {current.song.title} — {current.song.artist}
            </p>
          )}

          {current?.song &&
            (current.song.syncedLyrics || current.song.plainLyrics) && (
              <LyricsFeedbackRow queueItemId={Number(current.id)} />
            )}
        </div>
      )}
    </div>
  );
};

export default HandoffScreen;
