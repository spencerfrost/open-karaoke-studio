import React, { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Check, ExternalLink, FlaskConical, Play, Volume2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { cn } from "@/lib/utils";
import type {
  PreviewTrack,
  SongAudioPreviewHandle,
} from "@/features/songs/components/song-card/SongAudioPreview";
import {
  useSaveVocalRangeAnswers,
  useVocalRangeSong,
  useVocalRangeSongs,
  type MomentAnswer,
  type RangeMoment,
  type RangeResult,
  type SongKind,
  type VocalRangeSong,
  type VocalRangeSongRow,
} from "@/hooks/api/useVocalRangeReview";
import {
  FilterChips,
  ReviewEmpty,
  ReviewLayout,
  type ReviewSelection,
} from "./review/ReviewLayout";
import { SongSummary } from "./review/SongPanel";
import { StemPreview } from "./review/StemPreview";
import { clock } from "./review/clock";
import {
  usePlayhead,
  usePlayheadInside,
  usePlayheadTime,
  type Playhead,
} from "./review/usePlayhead";

/** A moment's clip starts this long before it and runs this long after. */
const CLIP_BEFORE_SECONDS = 1;
const CLIP_AFTER_SECONDS = 1;
/** The tracks a moment can be played on, from its own buttons. */
const CLIP_TRACKS: { track: PreviewTrack; label: string }[] = [
  { track: "vocals", label: "Vocals" },
  { track: "original", label: "Original" },
  { track: "backing-vocals", label: "Backing" },
];

/** How long a reference tone sounds. */
const TONE_SECONDS = 1.2;

const MOMENT_ANSWERS: { answer: MomentAnswer; label: string }[] = [
  { answer: "right", label: "Right note" },
  { answer: "octave_high", label: "Too high: sung an octave lower" },
  { answer: "octave_low", label: "Too low: sung an octave higher" },
  { answer: "wrong_note", label: "A different note" },
  { answer: "not_singer", label: "Not the singer" },
  { answer: "no_note", label: "Rapped or spoken: no note" },
  { answer: "screamed", label: "Screamed or yelled: no clear note" },
  { answer: "cant_tell", label: "Can't tell" },
];
const MOMENT_LABEL = Object.fromEntries(
  MOMENT_ANSWERS.map(({ answer, label }) => [answer, label]),
) as Record<MomentAnswer, string>;

const KINDS: { kind: SongKind; label: string }[] = [
  { kind: "sung", label: "Sung" },
  { kind: "mixed", label: "Rap with a sung part" },
  { kind: "rapped", label: "Rapped" },
  { kind: "spoken", label: "Spoken" },
  { kind: "instrumental", label: "No vocals" },
];
const KIND_LABEL = Object.fromEntries(
  KINDS.map(({ kind, label }) => [kind, label]),
) as Record<SongKind, string>;

const NO_MOMENTS: RangeMoment[] = [];

/** Methods checked unless the URL says otherwise: today's, and the best so far. */
const DEFAULT_METHODS = ["baseline", "notes+lead+labels"];
const METHODS_PARAM = "methods";

/** How the reference was found, from reference.json's `confidence`. */
const CONFIDENCE: Record<string, string> = {
  page: "read on the listing",
  search: "from a search result, listing not opened",
  conflicting: "listings disagree; the original key's picked",
};

const isDone = (row: VocalRangeSongRow) =>
  row.answered >= row.moments && row.kind !== null;

function describeRange(result: RangeResult | null | undefined): string {
  if (!result) return "not run";
  if (result.label) return result.label;
  if (!result.low || !result.high) return "no range";
  return `${result.low}–${result.high}`;
}

function describeRow(row: VocalRangeSongRow, methods: string[]) {
  const range = methods.map((m) => describeRange(row.results[m])).join(" → ");
  const progress = isDone(row)
    ? "all checked"
    : `${row.answered} of ${row.moments} moments${row.kind ? "" : ", kind not set"}`;
  return `${range} · ${progress}`;
}

// --- Reference tones -------------------------------------------------------

let audioContext: AudioContext | null = null;

/** A short tone at a MIDI note, to hold a sung note up against. */
function playTone(midi: number) {
  audioContext ??= new AudioContext();
  const ctx = audioContext;
  const now = ctx.currentTime;
  const oscillator = ctx.createOscillator();
  const gain = ctx.createGain();
  oscillator.type = "triangle";
  oscillator.frequency.value = 440 * 2 ** ((midi - 69) / 12);
  gain.gain.setValueAtTime(0, now);
  gain.gain.linearRampToValueAtTime(0.25, now + 0.03);
  gain.gain.setValueAtTime(0.25, now + TONE_SECONDS - 0.15);
  gain.gain.linearRampToValueAtTime(0, now + TONE_SECONDS);
  oscillator.connect(gain).connect(ctx.destination);
  oscillator.start(now);
  oscillator.stop(now + TONE_SECONDS);
}

const NAMES = ["C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯", "A", "A♯", "B"];
const noteName = (midi: number) =>
  `${NAMES[((midi % 12) + 12) % 12]}${Math.floor(midi / 12) - 1}`;

// --- Pitch strip -----------------------------------------------------------

const STRIP_WIDTH = 600;
const STRIP_HEIGHT = 120;

/**
 * The pitch track around a moment: a dot per frame (faint where the tracker
 * wasn't sure), the moment's note as a line with the octaves either side,
 * and the moment itself shaded. A held note reads as a flat run of dots, an
 * octave error as a jump and back.
 */
const PitchStrip: React.FC<{
  moment: RangeMoment;
  playhead: Playhead;
}> = ({ moment, playhead }) => {
  const contour = moment.contour;
  if (!contour) {
    return (
      <p className="text-xs text-muted-foreground">No pitch track saved.</p>
    );
  }
  const notes = contour.points.map((p) => p[1]);
  const lowest = Math.min(moment.midi - 12, ...notes) - 1;
  const highest = Math.max(moment.midi + 12, ...notes) + 1;
  const length = Math.max(0.1, contour.end - contour.start);
  const x = (t: number) => ((t - contour.start) / length) * STRIP_WIDTH;
  const y = (m: number) =>
    STRIP_HEIGHT - ((m - lowest) / (highest - lowest)) * STRIP_HEIGHT;

  return (
    <svg
      viewBox={`0 0 ${STRIP_WIDTH} ${STRIP_HEIGHT}`}
      preserveAspectRatio="none"
      className="h-28 w-full rounded-sm bg-muted/50"
      role="img"
      aria-label={`Pitch track around ${moment.note}`}
    >
      <rect
        x={x(moment.start)}
        width={Math.max(2, x(moment.start + moment.duration) - x(moment.start))}
        y={0}
        height={STRIP_HEIGHT}
        className="fill-primary/15"
      />
      {[-12, 12].map((offset) => (
        <line
          key={offset}
          x1={0}
          x2={STRIP_WIDTH}
          y1={y(moment.midi + offset)}
          y2={y(moment.midi + offset)}
          className="stroke-border"
          strokeDasharray="4 4"
          vectorEffect="non-scaling-stroke"
        />
      ))}
      <line
        x1={0}
        x2={STRIP_WIDTH}
        y1={y(moment.midi)}
        y2={y(moment.midi)}
        className="stroke-primary"
        vectorEffect="non-scaling-stroke"
      />
      {contour.points.map(([t, m, confident], i) => (
        <rect
          key={i}
          x={x(t) - 1.5}
          y={y(m) - 1.5}
          width={3}
          height={3}
          className={confident ? "fill-foreground" : "fill-muted-foreground/40"}
        />
      ))}
      <StripPlayhead
        playhead={playhead}
        start={contour.start}
        end={contour.end}
        x={x}
      />
    </svg>
  );
};

const StripPlayhead: React.FC<{
  playhead: Playhead;
  start: number;
  end: number;
  x: (t: number) => number;
}> = ({ playhead, start, end, x }) => {
  const inside = usePlayheadInside(playhead, start, end);
  return inside ? <StripPlayheadLine playhead={playhead} x={x} /> : null;
};

const StripPlayheadLine: React.FC<{
  playhead: Playhead;
  x: (t: number) => number;
}> = ({ playhead, x }) => {
  const time = usePlayheadTime(playhead);
  return (
    <line
      x1={x(time)}
      x2={x(time)}
      y1={0}
      y2={STRIP_HEIGHT}
      className="stroke-foreground"
      strokeWidth={2}
      vectorEffect="non-scaling-stroke"
    />
  );
};

// --- A moment --------------------------------------------------------------

function describeSets(moment: RangeMoment): string {
  const byEnd = (end: "low" | "high") =>
    moment.sets.filter((s) => s.end === end).map((s) => s.method);
  const parts = [];
  const low = byEnd("low");
  const high = byEnd("high");
  if (low.length) parts.push(`lowest note for ${low.join(", ")}`);
  if (high.length) parts.push(`highest note for ${high.join(", ")}`);
  return parts.join(" · ");
}

const MomentRow: React.FC<{
  moment: RangeMoment;
  playhead: Playhead;
  playClip: (start: number, end: number, track: PreviewTrack) => void;
  onAnswer: (answer: MomentAnswer | null) => void;
  saving: boolean;
}> = ({ moment, playhead, playClip, onAnswer, saving }) => {
  const end = moment.start + moment.duration;
  const playing = usePlayheadInside(
    playhead,
    moment.start - CLIP_BEFORE_SECONDS,
    end + CLIP_AFTER_SECONDS,
  );
  return (
    <li
      className={cn(
        "space-y-3 rounded-md border px-3 py-2.5 transition-colors",
        playing ? "border-primary/60 bg-primary/10" : "border-border/60",
      )}
    >
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <span className="text-xl font-semibold tabular-nums">
          {moment.note}
        </span>
        <span className="min-w-0 flex-1 text-sm text-muted-foreground">
          {clock(moment.start)}, held {moment.duration.toFixed(2)} s ·{" "}
          {describeSets(moment)}
        </span>
        {moment.answer && (
          <Badge variant="secondary">
            <Check />
            {MOMENT_LABEL[moment.answer]}
          </Badge>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm text-muted-foreground">Play</span>
        {CLIP_TRACKS.map(({ track, label }) => (
          <Button
            key={track}
            size="sm"
            variant="outline"
            onClick={() =>
              playClip(
                moment.start - CLIP_BEFORE_SECONDS,
                end + CLIP_AFTER_SECONDS,
                track,
              )
            }
          >
            <Play className="size-3.5" />
            {label}
          </Button>
        ))}
        {[
          {
            offset: -12,
            label: `${noteName(moment.midi - 12)} (octave lower)`,
          },
          { offset: 0, label: moment.note },
          {
            offset: 12,
            label: `${noteName(moment.midi + 12)} (octave higher)`,
          },
        ].map(({ offset, label }) => (
          <Button
            key={offset}
            size="sm"
            variant="ghost"
            onClick={() => playTone(moment.midi + offset)}
          >
            <Volume2 className="size-3.5" />
            Tone {label}
          </Button>
        ))}
      </div>
      <PitchStrip moment={moment} playhead={playhead} />
      <ToggleGroup
        type="single"
        variant="outline"
        size="sm"
        value={moment.answer ?? ""}
        disabled={saving}
        // Pressing the chosen answer again clears it.
        onValueChange={(value) => onAnswer((value as MomentAnswer) || null)}
        aria-label="Is this the note the singer sings here"
        className="flex-wrap"
      >
        {MOMENT_ANSWERS.map(({ answer, label }) => (
          <ToggleGroupItem key={answer} value={answer} className="px-3">
            {label}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
    </li>
  );
};

// --- A song ----------------------------------------------------------------

const Ranges: React.FC<{ song: VocalRangeSong }> = ({ song }) => {
  const reference = song.reference;
  const referenceRange =
    reference?.low && reference.high
      ? `${reference.low}–${reference.high}`
      : null;
  const verdict = (answer: MomentAnswer | null) =>
    answer ? MOMENT_LABEL[answer] : "–";
  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1.5 text-sm">
      <dt className="text-muted-foreground">Stored today</dt>
      <dd className="tabular-nums">
        {song.stored ? `${song.stored.low}–${song.stored.high}` : "none"}
      </dd>
      {referenceRange && (
        <>
          <dt className="text-muted-foreground">Sheet music</dt>
          <dd>
            <span className="tabular-nums">{referenceRange}</span>{" "}
            <span className="text-muted-foreground">
              (the notes and span are useful; the octave often isn&apos;t
              {reference?.confidence && CONFIDENCE[reference.confidence]
                ? `; ${CONFIDENCE[reference.confidence]}`
                : ""}
              )
            </span>
            {reference?.url && (
              <a
                href={reference.url}
                target="_blank"
                rel="noreferrer"
                className="ml-1 inline-flex items-center gap-0.5 text-primary hover:underline"
              >
                source
                <ExternalLink className="size-3" />
              </a>
            )}
          </dd>
        </>
      )}
      {song.methods.map((m) => (
        <React.Fragment key={m.method}>
          <dt className="text-muted-foreground" title={m.description}>
            {m.method}
          </dt>
          <dd>
            <span className="tabular-nums">{describeRange(m.result)}</span>
            {m.result?.low && (
              <span className="text-muted-foreground">
                {" "}
                · low: {verdict(m.verdicts.low)} · high:{" "}
                {verdict(m.verdicts.high)}
              </span>
            )}
          </dd>
        </React.Fragment>
      ))}
    </dl>
  );
};

const SongDetail: React.FC<{
  row: VocalRangeSongRow;
  methods: string[];
  selection: ReviewSelection;
  onAnswered: () => void;
}> = ({ row, methods, selection, onAnswered }) => {
  const {
    data: song,
    isLoading,
    error,
  } = useVocalRangeSong(row.songId, methods);
  const save = useSaveVocalRangeAnswers(row.songId, methods);
  const [showBackups, setShowBackups] = useState(false);
  const player = useRef<SongAudioPreviewHandle>(null);
  const playhead = usePlayhead();
  const [track, setTrack] = useState<PreviewTrack>("vocals");
  // The clip asked for; it counts as started once playback reaches it (a
  // track switch reports a few stray positions first). null: playing freely.
  const clip = useRef<{ start: number; end: number; started: boolean } | null>(
    null,
  );
  // A clip waiting for its track to be switched to.
  const [pendingClip, setPendingClip] = useState<{
    start: number;
    end: number;
  } | null>(null);

  const onTimeChange = useCallback(
    (seconds: number) => {
      playhead.set(seconds);
      const current = clip.current;
      if (!current) return;
      if (!current.started) {
        if (seconds >= current.start - 0.25 && seconds < current.end) {
          current.started = true;
        }
        return;
      }
      if (seconds < current.start - 0.5 || seconds > current.end + 1.5) {
        // Moved elsewhere by hand: play on.
        clip.current = null;
      } else if (seconds >= current.end) {
        clip.current = null;
        player.current?.pause();
      }
    },
    [playhead],
  );

  const startClip = (start: number, end: number) => {
    clip.current = { start: Math.max(0, start), end, started: false };
    player.current?.playFrom(Math.max(0, start));
  };

  const playClip = (start: number, end: number, clipTrack: PreviewTrack) => {
    if (clipTrack === track) {
      startClip(start, end);
      return;
    }
    // Switch first; the player takes the jump once the new track is set.
    setTrack(clipTrack);
    setPendingClip({ start, end });
  };

  useEffect(() => {
    if (!pendingClip) return;
    setPendingClip(null);
    startClip(pendingClip.start, pendingClip.end);
    // Runs once the track switch has rendered; startClip only reads refs.
  }, [pendingClip]);

  const answer = (key: string, value: MomentAnswer | SongKind | null) => {
    onAnswered();
    save.mutate({ answers: [{ key, answer: value }], methods });
  };

  const moments = song?.moments ?? NO_MOMENTS;
  const primary = moments.filter((m) => m.primary);
  const backups = moments.length - primary.length;
  const shownMoments = showBackups ? moments : primary;
  const done = song && primary.every((m) => m.answer) && song.kind !== null;

  return (
    <div className="space-y-5">
      <SongSummary
        basics={{ id: row.songId, title: row.title, artist: row.artist }}
        size="sm"
      />
      <StemPreview
        songId={row.songId}
        onTimeChange={onTimeChange}
        playerRef={player}
        track={track}
        onTrackChange={setTrack}
      />

      {isLoading && <p className="text-sm text-muted-foreground">Loading…</p>}
      {error && (
        <p className="text-sm text-destructive-strong">
          Couldn&apos;t load this song: {error.message}
        </p>
      )}
      {save.error && (
        <p className="text-sm text-destructive-strong">
          Couldn&apos;t save that: {save.error.message}
        </p>
      )}

      {song && (
        <>
          <Ranges song={song} />

          <section className="space-y-2">
            <h3 className="font-semibold">What kind of song is it?</h3>
            {song.reference?.kind && song.reference.kind !== "sung" && (
              <p className="text-sm text-muted-foreground">
                Expected:{" "}
                {KIND_LABEL[song.reference.kind as SongKind] ??
                  song.reference.kind}
                {song.reference.notes ? `. ${song.reference.notes}` : ""}
              </p>
            )}
            <ToggleGroup
              type="single"
              variant="outline"
              size="sm"
              value={song.kind ?? ""}
              disabled={save.isPending}
              onValueChange={(value) =>
                answer("kind", (value as SongKind) || null)
              }
              aria-label="What kind of song it is"
              className="flex-wrap"
            >
              {KINDS.map(({ kind, label }) => (
                <ToggleGroupItem key={kind} value={kind} className="px-3">
                  {label}
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
          </section>

          <section className="space-y-3">
            <h3 className="font-semibold">The moments that set the range</h3>
            <p className="text-sm text-muted-foreground">
              The longest stretch at each method&apos;s lowest and highest note.
            </p>
            {done && (
              <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-success/40 bg-success/10 px-3 py-2">
                <p className="text-sm">All checked. Thanks!</p>
                <Button size="sm" onClick={selection.done}>
                  Next song
                </Button>
              </div>
            )}
            {moments.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No method found a range here, so there&apos;s nothing to play.
              </p>
            ) : (
              <ol className="space-y-2">
                {shownMoments.map((moment) => (
                  <MomentRow
                    key={moment.key}
                    moment={moment}
                    playhead={playhead}
                    playClip={playClip}
                    saving={save.isPending}
                    onAnswer={(value) => answer(moment.key, value)}
                  />
                ))}
              </ol>
            )}
            {backups > 0 && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setShowBackups((shown) => !shown)}
              >
                {showBackups
                  ? "Hide the backup moments"
                  : `Show ${backups} backup ${backups === 1 ? "moment" : "moments"} (for when a first one can't be told)`}
              </Button>
            )}
          </section>
        </>
      )}
    </div>
  );
};

// --- The page --------------------------------------------------------------

/**
 * The vocal range benchmark's answers, checked by ear: for each test song, the
 * moments each method says set its lowest and highest note. Play one, hold it
 * up against a tone, and say whether the note is right. The benchmark writes
 * its results to a folder on the machine it ran on; nothing here reaches the TV.
 */
const AdminCheckVocalRangePage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const methodsParam = searchParams.get(METHODS_PARAM);
  const methods = methodsParam ? methodsParam.split(",") : DEFAULT_METHODS;
  const { data, isLoading, error } = useVocalRangeSongs(methods);
  const [filter, setFilter] = useState("to-check");
  // A song stays listed while it's open, even once it's checked.
  const [pinned, setPinned] = useState<string | null>(null);
  const selectedId = searchParams.get("song");
  const keep = pinned && (selectedId === null || selectedId === pinned);

  const songs = data?.songs;
  const shownMethods = (data?.methods ?? []).map((m) => m.method);
  const allMethods = data?.allMethods ?? [];

  const chooseMethods = (values: string[]) => {
    if (values.length === 0) return;
    const ordered = allMethods
      .map((m) => m.method)
      .filter((m) => values.includes(m));
    const next = new URLSearchParams(searchParams);
    next.set(METHODS_PARAM, ordered.join(","));
    setSearchParams(next, { replace: true });
  };

  const matches = (row: VocalRangeSongRow) => {
    if (filter === "to-check") return !isDone(row);
    if (filter === "checked") return row.answered > 0 || row.kind !== null;
    if (filter === "all") return true;
    return row.group === filter;
  };
  const shown = songs?.filter((row) => matches(row) || row.songId === keep);

  return (
    <ReviewLayout
      label="Songs to check the vocal range of"
      items={isLoading ? undefined : shown}
      getId={(row) => row.songId}
      isLoading={isLoading}
      error={error}
      toolbar={
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Each song lists the moments that set its lowest and highest note.
            Play each one on the vocals track, or on Original when the singing
            there is faint or odd (the separation isn&apos;t perfect), play the
            tones to compare, and say whether the singer&apos;s note is right.
            Then say what kind of song it is, as heard on Original.
          </p>
          {allMethods.length > 1 && (
            <div className="space-y-1">
              <p className="text-sm font-medium">Methods to check</p>
              <ToggleGroup
                type="multiple"
                variant="outline"
                size="sm"
                value={shownMethods}
                onValueChange={chooseMethods}
                aria-label="Which methods' moments to check"
                className="flex-wrap"
              >
                {allMethods.map((m) => (
                  <ToggleGroupItem
                    key={m.method}
                    value={m.method}
                    title={m.description}
                    className="px-3"
                  >
                    {m.method}
                  </ToggleGroupItem>
                ))}
              </ToggleGroup>
            </div>
          )}
          {(data?.methods ?? []).map((m) => {
            const verdicts = data?.verdicts[m.method] ?? {};
            const judged = Object.values(verdicts).reduce(
              (sum, n) => sum + (n ?? 0),
              0,
            );
            if (judged === 0) return null;
            return (
              <div
                key={m.method}
                className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm"
              >
                <span className="font-medium" title={m.description}>
                  {m.method}, {judged} ends judged:
                </span>
                {MOMENT_ANSWERS.filter(({ answer }) => verdicts[answer]).map(
                  ({ answer, label }) => (
                    <span key={answer} className="text-muted-foreground">
                      {label}{" "}
                      <span className="font-medium tabular-nums text-foreground">
                        {verdicts[answer]}
                      </span>
                    </span>
                  ),
                )}
              </div>
            );
          })}
        </div>
      }
      filters={
        data &&
        !!songs?.length && (
          <FilterChips
            label="Show songs"
            value={filter}
            onChange={setFilter}
            chips={[
              {
                value: "to-check",
                label: "To check",
                count: songs.filter((r) => !isDone(r)).length,
              },
              {
                value: "checked",
                label: "Checked",
                count: songs.filter((r) => r.answered > 0 || r.kind !== null)
                  .length,
              },
              ...data.groups
                .map((group) => ({
                  value: group.key,
                  label: group.label,
                  count: songs.filter((r) => r.group === group.key).length,
                }))
                .filter((chip) => chip.count > 0),
              { value: "all", label: "All", count: songs.length },
            ]}
          />
        )
      }
      empty={
        <ReviewEmpty
          icon={FlaskConical}
          title={
            songs?.length ? "No songs here" : "No benchmark on this machine"
          }
        >
          {songs?.length
            ? "Try another filter."
            : "The vocal range benchmark (backend/scripts/experiments/vocal_range) writes its results on the machine that runs it. Run it here first."}
        </ReviewEmpty>
      }
      renderRow={(row) => (
        <>
          <p className="truncate text-sm font-medium">{row.title}</p>
          <p className="truncate text-xs text-muted-foreground">{row.artist}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {describeRow(row, shownMethods)}
          </p>
        </>
      )}
      renderDetail={(row, selection) => (
        <SongDetail
          row={row}
          methods={methods}
          selection={{
            ...selection,
            done: () => {
              setPinned(null);
              selection.done();
            },
          }}
          onAnswered={() => setPinned(row.songId)}
        />
      )}
    />
  );
};

export default AdminCheckVocalRangePage;
