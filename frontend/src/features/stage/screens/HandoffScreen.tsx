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
 *   3. How to change either - quiet, always present, never a modal.
 *
 * No clock runs here. This is a living-room app: the screen waits until
 * someone taps, rather than playing the next song or passing over a person who
 * hasn't picked one yet.
 *
 * See docs/plans/2026-08-29-handoff-screen.md.
 */

import React, { useCallback, useMemo, useState } from "react";
import { Library, Music, Play, UserRoundX, Users } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { QRCodeDisplay } from "@/features/queue";
import { useSongs } from "@/hooks/api/useSongs";
import { useAddToKaraokeQueue } from "@/hooks/api/useKaraokeQueue";
import {
  useClaimTurn,
  useDeactivatePerformer,
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
import RosterPicker from "../components/RosterPicker";
import { useStageShell } from "../StageShellContext";

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

  const claimTurn = useClaimTurn(displayCode || undefined);
  const deactivatePerformer = useDeactivatePerformer(displayCode || undefined);
  const addToQueue = useAddToKaraokeQueue(displayCode || undefined);

  const [isPicking, setIsPicking] = useState(false);
  const [pickedName, setPickedName] = useState("");
  const [showOther, setShowOther] = useState(false);

  const nextItem = upcoming.find((item) => Number(item.id) === turn.itemId);
  const hasSong = turn.kind === "queued" && Boolean(nextItem);

  // A 409 means somebody else got there first. Both screens are about to be
  // told the same thing by the queue broadcast, so there is nothing to say.
  const onTurnError = useCallback((error: Error, action: string) => {
    if (error instanceof TurnMovedOnError) {
      logger.debug("%s lost the race; the broadcast will settle it", action);
      return;
    }
    logger.error("%s failed:", action, error);
    toast.error(`Couldn't ${action}. Try again.`);
  }, []);

  const handleAdvance = useCallback(() => {
    if (nextItem) onPlayFromQueue(nextItem.id);
  }, [nextItem, onPlayFromQueue]);

  const handleClaim = useCallback(
    (opts: { performerId?: number; name?: string }) => {
      claimTurn.mutate(
        { expectedPerformerId: turn.performerId, ...opts },
        {
          onSuccess: () => {
            setIsPicking(false);
            setShowOther(false);
            setPickedName("");
          },
          onError: (e) => onTurnError(e, "take the turn"),
        },
      );
    },
    [claimTurn, turn.performerId, onTurnError],
  );

  const handleSkipMe = useCallback(() => {
    if (turn.performerId === null) return;
    deactivatePerformer.mutate(turn.performerId, {
      onError: (e) => onTurnError(e, "step out"),
    });
  }, [deactivatePerformer, turn.performerId, onTurnError]);

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

  // Two or three ahead, so people can get ready. Free: the list is sorted.
  const onDeck = useMemo(
    () =>
      upcoming
        .filter((item) => Number(item.id) !== turn.itemId)
        .slice(0, 3)
        .map((item) => item.singer),
    [upcoming, turn.itemId],
  );

  // An audience of one should not be told about a rotation.
  const showRibbon = turn.circle.length >= 2;

  return (
    <div className="flex h-full w-full flex-col items-center justify-center gap-10 overflow-auto p-10">
      {/* ---- Slot 1: who's up ------------------------------------------- */}
      <div className="text-center">
        {turn.performerName ? (
          <>
            <p className="text-xl uppercase tracking-[0.2em] text-foreground/45">
              Up next
            </p>
            <h1 className="font-display text-8xl leading-none text-primary">
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
        {isPicking ? (
          <div className="w-full max-w-2xl space-y-4 text-center">
            <p className="text-xl text-foreground/60">Who's up, then?</p>
            <RosterPicker
              roster={roster}
              value={pickedName}
              onChange={setPickedName}
              showOther={showOther}
              onShowOtherChange={setShowOther}
              excludeIds={turn.performerId ? [turn.performerId] : []}
            />
            <div className="flex justify-center gap-3 pt-2">
              <Button variant="ghost" onClick={() => setIsPicking(false)}>
                Never mind
              </Button>
              <Button
                variant="primary"
                size="lg"
                disabled={!pickedName.trim() || claimTurn.isPending}
                onClick={() => {
                  const match = roster.find((p) => p.name === pickedName);
                  handleClaim(
                    match
                      ? { performerId: match.id }
                      : { name: pickedName.trim() },
                  );
                }}
              >
                That's me
              </Button>
            </div>
          </div>
        ) : hasSong && nextItem ? (
          <button
            onClick={handleAdvance}
            className="group flex items-center gap-8 rounded-xl p-2 text-left"
            aria-label={`Play ${nextItem.song.title}`}
          >
            <div className="relative flex size-48 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-overlay/60 shadow-2xl">
              {getArtworkUrl(nextItem.song, "large") ? (
                <img
                  src={getArtworkUrl(nextItem.song, "large") ?? undefined}
                  alt=""
                  className="size-full object-cover transition-transform duration-300 group-hover:scale-105"
                />
              ) : (
                <Music size={64} className="text-foreground/20" />
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
              <h2 className="font-display text-5xl leading-tight text-foreground">
                {nextItem.song.title}
              </h2>
              <p className="pt-2 text-2xl text-foreground/55">
                {nextItem.song.artist}
              </p>
            </div>
          </button>
        ) : turn.kind === "open" && roster.length === 0 && displayCode ? (
          <div className="flex flex-col items-center gap-5">
            <p className="text-2xl text-foreground/60">
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
            <p className="text-2xl text-foreground/60">
              {turn.performerName
                ? `${turn.performerName} — check your phone, or pick one here`
                : "Pick something to keep it going"}
            </p>

            {suggestions.length > 0 && (
              <div className="w-full">
                <h3 className="pb-3 text-center text-lg text-foreground/50">
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
                            <Music size={32} className="text-foreground/30" />
                          </div>
                        )}
                      </div>
                      <div className="p-2">
                        <p className="truncate text-base font-medium text-foreground">
                          {song.title}
                        </p>
                        <p className="truncate text-sm text-foreground/60">
                          {song.artist}
                        </p>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {suggestionsLoading && (
              <p className="text-foreground/50">Finding more songs…</p>
            )}

            <Button
              variant="outline"
              size="lg"
              onClick={() => shell?.openSelect()}
              className="gap-2"
            >
              <Library className="size-5" />
              Browse Library
            </Button>
          </div>
        )}
      </div>

      {/* ---- Slot 3: how to change either -------------------------------- */}
      {!isPicking && (
        <div className="flex w-full max-w-4xl flex-col items-center gap-4">
          {turn.performerId !== null && (
            <div className="flex items-center gap-3">
              <Button
                variant="ghost"
                size="lg"
                onClick={() => {
                  setPickedName("");
                  setShowOther(roster.length <= 1);
                  setIsPicking(true);
                }}
                className="gap-2 text-foreground/60 hover:text-foreground"
              >
                <Users className="size-5" />
                That's not me
              </Button>
              <span className="text-foreground/20">·</span>
              <Button
                variant="ghost"
                size="lg"
                onClick={handleSkipMe}
                disabled={deactivatePerformer.isPending}
                className="gap-2 text-foreground/60 hover:text-foreground"
              >
                <UserRoundX className="size-5" />
                Skip me for now
              </Button>
            </div>
          )}

          {onDeck.length > 0 && (
            <p className="text-lg text-foreground/40">
              On deck:{" "}
              <span className="text-foreground/70">{onDeck.join(" · ")}</span>
            </p>
          )}

          {showRibbon && (
            <p
              className={cn(
                "text-base uppercase tracking-[0.15em] text-foreground/30",
              )}
            >
              {turn.circle.map((p) => p.name).join(" → ")} →{" "}
              {turn.circle[0].name}
            </p>
          )}

          {current?.song && (
            <p className="pt-2 text-sm text-foreground/25">
              Just played: {current.song.title} — {current.song.artist}
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default HandoffScreen;
