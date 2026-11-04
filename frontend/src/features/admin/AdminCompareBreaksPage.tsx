import React, {
  useCallback,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import { useSearchParams } from "react-router-dom";
import { AudioLines, Check, Play } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { cn } from "@/lib/utils";
import {
  useSaveBreakChecks,
  useSingingMapSong,
  useSingingMapSongs,
  type BreakCheckAnswer,
  type BreaksMoment,
  type SingingMapSong,
  type SingingMapSongRow,
  type Span,
} from "@/hooks/api/useSingingMap";
import type { SongAudioPreviewHandle } from "@/features/songs/components/song-card/SongAudioPreview";
import {
  FilterChips,
  ReviewEmpty,
  ReviewLayout,
  type ReviewSelection,
} from "./review/ReviewLayout";
import { SongSummary } from "./review/SongPanel";
import { StemPreview } from "./review/StemPreview";

type Filter =
  | "to-check"
  | "checked"
  | "no-word-timing"
  | "no-breaks-today"
  | "all";

/** How far before a moment playback starts, to hear it arrive. */
const PLAY_BEFORE_SECONDS = 3;

const FILTERS: Record<Filter, (row: SingingMapSongRow) => boolean> = {
  "to-check": (row) => row.measured && row.toCheck > 0,
  checked: (row) => row.answers.length > 0 && row.toCheck === 0,
  "no-word-timing": (row) => !row.hasWordTiming,
  "no-breaks-today": (row) => row.hasWordTiming && row.wordGapBreaks === 0,
  all: () => true,
};

/** "1:16.4" */
function clock(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const rest = (seconds - minutes * 60).toFixed(1).padStart(4, "0");
  return `${minutes}:${rest}`;
}

const span = ([start, end]: Span) => `${clock(start)}–${clock(end)}`;

/** The answers a moment can take, in the words its buttons say. */
function answerOptions(
  moment: BreaksMoment,
): { answer: BreakCheckAnswer; label: string }[] {
  if (moment.kind === "break") {
    return [
      { answer: "map_right", label: "Map is right" },
      { answer: "today_right", label: "Today is right" },
      { answer: "both_wrong", label: "Both wrong" },
      { answer: "either_fine", label: "Either is fine" },
    ];
  }
  return moment.onScreen
    ? [
        { answer: "lyrics_match", label: "Lyrics match the backing" },
        { answer: "lyrics_dont_match", label: "They don't" },
      ]
    : [
        { answer: "bar_fine", label: "A bar here is fine" },
        { answer: "no_bar", label: "Shouldn't be a bar" },
      ];
}

/** The answer that says the map got this moment right. */
function mapIsRight(moment: BreaksMoment): BreakCheckAnswer {
  if (moment.kind === "break") return "map_right";
  return moment.onScreen ? "lyrics_match" : "bar_fine";
}

const needsAnswer = (moment: BreaksMoment) =>
  !(moment.kind === "break" && moment.agree);

const TALLY: { answer: BreakCheckAnswer; label: string }[] = [
  { answer: "map_right", label: "Map right" },
  { answer: "today_right", label: "Today right" },
  { answer: "both_wrong", label: "Both wrong" },
  { answer: "either_fine", label: "Either fine" },
  { answer: "bar_fine", label: "Backing: bar fine" },
  { answer: "no_bar", label: "Backing: no bar" },
  { answer: "lyrics_match", label: "Backing: lyrics match" },
  { answer: "lyrics_dont_match", label: "Backing: lyrics don't" },
];

function describeRow(row: SingingMapSongRow): string {
  if (!row.measured) return "Not measured yet";
  const toCheck =
    row.toCheck > 0
      ? `${row.toCheck} to check`
      : row.answers.length > 0
        ? "Checked"
        : "Nothing to check";
  const today = row.hasWordTiming
    ? `today ${row.wordGapBreaks}`
    : "no word timing";
  return `${toCheck} · map ${row.mapBreaks} · ${today}`;
}

/** What a moment is, in words, and what to listen for. */
function describeMoment(moment: BreaksMoment): {
  title: string;
  listen: string;
} {
  if (moment.kind === "backing_only") {
    return moment.onScreen
      ? {
          title: `Backing vocals only, ${span([moment.start, moment.end])}, with lyrics on screen`,
          listen: `Not a break: the screen shows “${moment.lineText}”. Is that what the backing sings?`,
        }
      : {
          title: `Backing vocals only, ${span([moment.start, moment.end])}, no lyrics on screen`,
          listen:
            "Doesn't count as singing, so it can be part of a break. Would you want a bar here?",
        };
  }
  if (moment.map && moment.wordGaps) {
    return moment.agree
      ? {
          title: `Break ${span(moment.map)}: both agree`,
          listen: "Nothing to decide. Listen if you want to check the bar.",
        }
      : {
          title: `Break: the map says ${span(moment.map)}, today says ${span(moment.wordGaps)}`,
          listen:
            "Listen to where the singing stops and starts again. Which is closer?",
        };
  }
  if (moment.map) {
    return {
      title: `Break ${span(moment.map)} from the map only`,
      listen:
        "The TV shows no bar here today. Is anyone singing? If not, the map is right.",
    };
  }
  return {
    title: `Break ${span(moment.wordGaps!)} shown today, not by the map`,
    listen:
      "The map hears singing here. If someone is singing, the map is right.",
  };
}

/**
 * The playing position, read by the parts that move with it (the timeline's
 * playhead, the moment being played) without re-rendering the whole panel
 * every frame.
 */
function usePlayhead() {
  const time = useRef(0);
  const listeners = useRef(new Set<() => void>());
  const set = useCallback((seconds: number) => {
    time.current = seconds;
    listeners.current.forEach((listener) => listener());
  }, []);
  const subscribe = useCallback((listener: () => void) => {
    listeners.current.add(listener);
    return () => listeners.current.delete(listener);
  }, []);
  const get = useCallback(() => time.current, []);
  return { set, subscribe, get };
}

type Playhead = ReturnType<typeof usePlayhead>;

function usePlayheadTime(playhead: Playhead): number {
  return useSyncExternalStore(playhead.subscribe, playhead.get);
}

function usePlayheadInside(playhead: Playhead, start: number, end: number) {
  return useSyncExternalStore(playhead.subscribe, () => {
    const t = playhead.get();
    return t >= start && t <= end;
  });
}

const MomentRow: React.FC<{
  moment: BreaksMoment;
  playhead: Playhead;
  playFrom: (seconds: number) => void;
  onAnswer: (answer: BreakCheckAnswer | null) => void;
  saving: boolean;
}> = ({ moment, playhead, playFrom, onAnswer, saving }) => {
  const playing = usePlayheadInside(
    playhead,
    moment.start - PLAY_BEFORE_SECONDS,
    moment.end,
  );
  const { title, listen } = describeMoment(moment);
  const differs = moment.kind === "break" && !moment.agree;
  const isBreak = moment.kind === "break";

  return (
    <li
      className={cn(
        "space-y-2 rounded-md border px-3 py-2.5 transition-colors",
        playing ? "border-primary/60 bg-primary/10" : "border-border/60",
      )}
    >
      <div className="flex flex-wrap items-start gap-2">
        <p className="min-w-0 flex-1 text-sm font-medium">{title}</p>
        {moment.answer && (
          <Badge variant="secondary">
            <Check />
            Answered
          </Badge>
        )}
        {differs && <Badge variant="accent">Differs</Badge>}
        {!isBreak && <Badge variant="outline">Backing</Badge>}
      </div>
      <p className="text-sm text-muted-foreground">{listen}</p>
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant="outline"
          onClick={() => playFrom(moment.start - PLAY_BEFORE_SECONDS)}
        >
          <Play className="size-3.5" />
          {isBreak ? "Play the start" : "Play"}
        </Button>
        {isBreak && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => playFrom(moment.end - PLAY_BEFORE_SECONDS)}
          >
            <Play className="size-3.5" />
            Play the end
          </Button>
        )}
      </div>
      {needsAnswer(moment) && (
        <ToggleGroup
          type="single"
          variant="outline"
          size="sm"
          value={moment.answer ?? ""}
          disabled={saving}
          // Pressing the chosen answer again clears it.
          onValueChange={(value) =>
            onAnswer((value as BreakCheckAnswer) || null)
          }
          aria-label="What you heard"
          className="flex-wrap"
        >
          {answerOptions(moment).map(({ answer, label }) => (
            <ToggleGroupItem key={answer} value={answer} className="px-3">
              {label}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      )}
    </li>
  );
};

const TimelineRow: React.FC<{
  label: string;
  duration: number;
  spans: { span: Span; className: string; title?: string }[];
}> = ({ label, duration, spans }) => (
  <>
    <span className="self-center text-xs text-muted-foreground">{label}</span>
    <div className="relative h-5 rounded-sm bg-muted/60">
      {spans.map(({ span: [start, end], className, title }, i) => (
        <div
          key={i}
          title={title}
          className={cn("absolute inset-y-0.5 rounded-[2px]", className)}
          style={{
            left: `${(start / duration) * 100}%`,
            width: `max(2px, ${((end - start) / duration) * 100}%)`,
          }}
        />
      ))}
    </div>
  </>
);

const Playheadline: React.FC<{ playhead: Playhead; duration: number }> = ({
  playhead,
  duration,
}) => {
  const time = usePlayheadTime(playhead);
  return (
    <div
      className="pointer-events-none absolute inset-y-0 w-0.5 bg-foreground"
      style={{ left: `${Math.min(100, (time / duration) * 100)}%` }}
    />
  );
};

/** One row per source, the playhead across all; click to play from there. */
const Timeline: React.FC<{
  song: SingingMapSong;
  duration: number;
  playhead: Playhead;
  playFrom: (seconds: number) => void;
}> = ({ song, duration, playhead, playFrom }) => {
  const toSpans = (
    spans: Span[],
    className: string,
  ): { span: Span; className: string }[] =>
    spans.map((s) => ({ span: s, className }));

  const breakSpans = (
    breaks: { start: number; end: number }[] | null,
  ): Span[] => (breaks ?? []).map((b) => [b.start, b.end]);

  const onClick = (event: React.MouseEvent<HTMLDivElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const ratio = (event.clientX - rect.left) / rect.width;
    if (ratio >= 0 && ratio <= 1) playFrom(ratio * duration);
  };

  return (
    <div className="space-y-2">
      <div className="relative">
        <div
          className="grid cursor-pointer grid-cols-[6.5rem_minmax(0,1fr)] gap-x-3 gap-y-1.5"
          onClick={onClick}
          role="presentation"
        >
          <TimelineRow
            label="Lead singing"
            duration={duration}
            spans={toSpans(song.lead, "bg-primary")}
          />
          <TimelineRow
            label="Backing singing"
            duration={duration}
            spans={[
              ...toSpans(song.backing ?? [], "bg-info/35"),
              ...toSpans(song.backingOnScreen, "bg-info"),
            ]}
          />
          <TimelineRow
            label="Breaks: map"
            duration={duration}
            spans={toSpans(breakSpans(song.mapBreaks), "bg-warning")}
          />
          <TimelineRow
            label="Breaks: today"
            duration={duration}
            spans={toSpans(
              breakSpans(song.wordGapBreaks),
              "bg-muted-foreground/70",
            )}
          />
          <TimelineRow
            label="Lyric lines"
            duration={duration}
            spans={song.lines.map((line) => ({
              span: [line.start, line.end],
              className: line.timed
                ? "bg-foreground/45 border-r border-background"
                : "bg-foreground/20 border-r border-background",
              title: `${clock(line.start)} ${line.text}`,
            }))}
          />
        </div>
        {/* Over the bars only, not the labels. */}
        <div className="pointer-events-none absolute inset-y-0 right-0 left-[calc(6.5rem+0.75rem)]">
          <Playheadline playhead={playhead} duration={duration} />
        </div>
      </div>
      <p className="text-xs text-muted-foreground">
        Click anywhere on the bars to play from there. Backing singing is
        brighter where a lyric line is on screen: only that part counts as
        singing for breaks.
        {song.backing === null && " This song has no backing vocals track."}
        {!song.hasWordTiming &&
          " No word timing, so line lengths come from the lyrics' timestamps and there are no breaks today."}
      </p>
    </div>
  );
};

const SongDetail: React.FC<{
  row: SingingMapSongRow;
  selection: ReviewSelection;
  /** Called on every answer, so the list keeps this song while it's open. */
  onAnswered: () => void;
}> = ({ row, selection, onAnswered }) => {
  const { data: song, isLoading, error } = useSingingMapSong(row.songId);
  const save = useSaveBreakChecks(row.songId);
  const player = useRef<SongAudioPreviewHandle>(null);
  const playhead = usePlayhead();
  const [showAgreed, setShowAgreed] = useState(false);

  const playFrom = (seconds: number) =>
    player.current?.playFrom(Math.max(0, seconds));

  const basics = { id: row.songId, title: row.title, artist: row.artist };
  const duration =
    song?.duration ??
    Math.max(0, ...(song?.lead.flat() ?? []), ...(song?.backing?.flat() ?? []));

  const moments = song?.moments ?? [];
  const agreed = moments.filter((m) => m.kind === "break" && m.agree);
  const shown = showAgreed ? moments : moments.filter(needsAnswer);
  const unanswered = moments.filter((m) => needsAnswer(m) && !m.answer);
  const allAnswered = moments.some(needsAnswer) && unanswered.length === 0;

  const answer = (
    answers: { key: string; answer: BreakCheckAnswer | null }[],
  ) => {
    onAnswered();
    save.mutate({ answers });
  };

  return (
    <div className="space-y-5">
      <SongSummary basics={basics} size="sm" />
      <StemPreview
        songId={row.songId}
        onTimeChange={playhead.set}
        playerRef={player}
      />

      {isLoading && (
        <p className="text-sm text-muted-foreground">
          {row.measured ? "Loading…" : "Measuring the singing, a few seconds…"}
        </p>
      )}
      {error && (
        <p className="text-sm text-destructive-strong">
          Couldn&apos;t load this song: {error.message}
        </p>
      )}

      {song && duration > 0 && (
        <>
          <Timeline
            song={song}
            duration={duration}
            playhead={playhead}
            playFrom={playFrom}
          />

          <section className="space-y-3">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h3 className="font-semibold">Moments to check</h3>
              {unanswered.length > 0 && (
                <Button
                  size="sm"
                  variant="outline"
                  disabled={save.isPending}
                  onClick={() =>
                    answer(
                      unanswered.map((m) => ({
                        key: m.key,
                        answer: mapIsRight(m),
                      })),
                    )
                  }
                >
                  <Check className="size-3.5" />
                  {unanswered.length === moments.filter(needsAnswer).length
                    ? "Map is right on all of these"
                    : `Map is right on the other ${unanswered.length}`}
                </Button>
              )}
              {agreed.length > 0 && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setShowAgreed((on) => !on)}
                >
                  {showAgreed
                    ? "Hide breaks both agree on"
                    : `Show ${agreed.length} ${agreed.length === 1 ? "break" : "breaks"} both agree on`}
                </Button>
              )}
            </div>
            {save.error && (
              <p className="text-sm text-destructive-strong">
                Couldn&apos;t save that: {save.error.message}
              </p>
            )}
            {allAnswered && (
              <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-success/40 bg-success/10 px-3 py-2">
                <p className="text-sm">All checked. Thanks!</p>
                <Button size="sm" onClick={selection.done}>
                  Next song
                </Button>
              </div>
            )}
            {shown.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Nothing to check: the map and today&apos;s breaks agree, and no
                backing vocals sing on their own.
              </p>
            ) : (
              <ol className="space-y-2">
                {shown.map((moment) => (
                  <MomentRow
                    key={moment.key}
                    moment={moment}
                    playhead={playhead}
                    playFrom={playFrom}
                    saving={save.isPending}
                    onAnswer={(value) =>
                      answer([{ key: moment.key, answer: value }])
                    }
                  />
                ))}
              </ol>
            )}
          </section>
        </>
      )}
    </div>
  );
};

/**
 * Instrumental breaks (the bar between lines on the TV) worked out two ways:
 * from the singing map (when the lead and backing vocals are singing, read
 * from the stems) and from gaps between aligned words, which is what the TV
 * shows today. For checking by ear which is better; it changes nothing.
 */
const AdminCompareBreaksPage: React.FC = () => {
  const { data, isLoading, error } = useSingingMapSongs();
  const [filter, setFilter] = useState<Filter>("to-check");
  const songs = data?.songs;
  const tally = data?.tally ?? {};
  const answered = Object.values(tally).reduce((sum, n) => sum + (n ?? 0), 0);
  // A song stays listed while it's open, even once it's checked, so the
  // list doesn't jump while you're still listening. Picking another song
  // (the URL's ?song=) lets it go.
  const [pinned, setPinned] = useState<string | null>(null);
  const [searchParams] = useSearchParams();
  const selectedId = searchParams.get("song");
  const keep = pinned && (selectedId === null || selectedId === pinned);
  const shown = songs?.filter(
    (row) => FILTERS[filter](row) || row.songId === keep,
  );

  return (
    <ReviewLayout
      label="Songs to compare breaks on"
      items={shown}
      getId={(row) => row.songId}
      isLoading={isLoading}
      error={error}
      toolbar={
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            The bar between lyric lines, worked out two ways: from when the
            vocals are actually singing (the map), and from gaps between the
            timed words (what the TV shows today). Each song lists the moments
            where they differ. Press play, listen, and say which was right.
          </p>
          {answered > 0 && (
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
              <span className="font-medium">
                Your answers so far ({answered}):
              </span>
              {TALLY.filter(({ answer }) => tally[answer]).map(
                ({ answer, label }) => (
                  <span key={answer} className="text-muted-foreground">
                    {label}{" "}
                    <span className="font-medium tabular-nums text-foreground">
                      {tally[answer]}
                    </span>
                  </span>
                ),
              )}
            </div>
          )}
        </div>
      }
      filters={
        !!songs?.length && (
          <FilterChips
            label="Show songs"
            value={filter}
            onChange={(value) => setFilter(value as Filter)}
            chips={[
              {
                value: "to-check",
                label: "To check",
                count: songs.filter(FILTERS["to-check"]).length,
              },
              {
                value: "checked",
                label: "Checked",
                count: songs.filter(FILTERS.checked).length,
              },
              {
                value: "no-word-timing",
                label: "No word timing",
                count: songs.filter(FILTERS["no-word-timing"]).length,
              },
              {
                value: "no-breaks-today",
                label: "No breaks today",
                count: songs.filter(FILTERS["no-breaks-today"]).length,
              },
              { value: "all", label: "All", count: songs.length },
            ]}
          />
        )
      }
      empty={
        <ReviewEmpty icon={AudioLines} title="No songs here">
          Only songs with synced lyrics are listed: without them there are no
          bars.
        </ReviewEmpty>
      }
      renderRow={(row) => (
        <>
          <p className="truncate text-sm font-medium">{row.title}</p>
          <p className="truncate text-xs text-muted-foreground">{row.artist}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {describeRow(row)}
          </p>
        </>
      )}
      renderDetail={(row, selection) => (
        <SongDetail
          row={row}
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

export default AdminCompareBreaksPage;
