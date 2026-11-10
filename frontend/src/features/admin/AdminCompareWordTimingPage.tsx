import React, { useRef, useState, useSyncExternalStore } from "react";
import { useSearchParams } from "react-router-dom";
import { Check, FlaskConical, Play } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { cn } from "@/lib/utils";
import { isWordTimingCrammed } from "@/features/lyrics/components/activeLineTiming";
import type { SongAudioPreviewHandle } from "@/features/songs/components/song-card/SongAudioPreview";
import type { WordTimestamp } from "@/utils/lrcParser";
import {
  useSaveWordTimingAnswers,
  useWordTimingExperiments,
  useWordTimingSong,
  useWordTimingSongs,
  type WordTimingAnswer,
  type WordTimingExperiment,
  type WordTimingMoment,
  type WordTimingSongRow,
} from "@/hooks/api/useWordTimingExperiments";
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
  usePlayheadTime,
  type Playhead,
} from "./review/usePlayhead";

/** How far before a line playback starts, to hear it arrive. */
const PLAY_BEFORE_SECONDS = 2;
/** How long a line stays the playing one after it ends, with nothing after it. */
const LINGER_SECONDS = 1;

/**
 * The one moment playing at `time`: the line being sung, else the next one
 * about to start, else the one just ended. Lines sung back to back overlap
 * their lead-ins, so "within a few seconds of it" alone would light two.
 */
function activeMomentKey(
  moments: WordTimingMoment[],
  time: number,
): string | null {
  const inside = moments.filter((m) => m.start <= time && time <= m.end);
  if (inside.length > 0) return inside[inside.length - 1].key;
  const next = moments.find(
    (m) => m.start > time && m.start - PLAY_BEFORE_SECONDS <= time,
  );
  if (next) return next.key;
  const ended = moments.filter(
    (m) => m.end < time && time <= m.end + LINGER_SECONDS,
  );
  return ended.length > 0 ? ended[ended.length - 1].key : null;
}

/** The playing moment's key; re-renders only when it changes. */
function useActiveMoment(
  playhead: Playhead,
  moments: WordTimingMoment[],
): string | null {
  return useSyncExternalStore(playhead.subscribe, () =>
    activeMomentKey(moments, playhead.get()),
  );
}

const EXPERIMENT_PARAM = "experiment";

const NO_MOMENTS: WordTimingMoment[] = [];

function answerOptions(
  experiment: WordTimingExperiment,
): { answer: WordTimingAnswer; label: string }[] {
  return [
    { answer: "b_right", label: `${experiment.b.label} is right` },
    { answer: "a_right", label: `${experiment.a.label} is right` },
    { answer: "both_wrong", label: "Both wrong" },
    { answer: "cant_tell", label: "Can't tell" },
  ];
}

const isDone = (row: WordTimingSongRow) =>
  row.moments > 0 && row.answered >= row.moments;

function describeRow(row: WordTimingSongRow): string {
  const progress =
    row.moments === 0
      ? "No lines differ"
      : isDone(row)
        ? `All ${row.moments} checked`
        : row.answered > 0
          ? `${row.answered} of ${row.moments} checked`
          : `${row.moments} ${row.moments === 1 ? "line differs" : "lines differ"}`;
  const bad =
    row.a.bad !== null && row.b.bad !== null
      ? ` · bad lines ${row.a.bad} → ${row.b.bad}`
      : "";
  return progress + bad;
}

/**
 * One timing of a line: each word as a block where it's timed, and the
 * words themselves lighting up as they're reached. Blocks share the
 * moment's time axis, so the two timings line up one above the other.
 */
const TimingRow: React.FC<{
  label: string;
  words: WordTimestamp[];
  start: number;
  end: number;
  time: number | null;
}> = ({ label, words, start, end, time }) => {
  const length = Math.max(0.1, end - start);
  const crammed = words.length >= 3 && isWordTimingCrammed(words);
  return (
    <div className="space-y-1">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-muted-foreground">
          {label}
        </span>
        {crammed && <Badge variant="accent">Crammed: the TV sweeps it</Badge>}
        {words.length === 0 && (
          <span className="text-xs text-muted-foreground">No words timed</span>
        )}
      </div>
      <div className="relative h-3 rounded-sm bg-muted/60">
        {words.map((word, i) => (
          <div
            key={i}
            title={`${word.word} ${clock(word.start)}–${clock(word.end)}${
              word.score !== undefined ? `, score ${word.score.toFixed(2)}` : ""
            }`}
            className={cn(
              "absolute inset-y-0.5 rounded-[2px] border-r border-background",
              word.score !== undefined && word.score < 0.1
                ? "bg-warning/70"
                : "bg-primary/70",
            )}
            style={{
              left: `${((word.start - start) / length) * 100}%`,
              width: `max(2px, ${((word.end - word.start) / length) * 100}%)`,
            }}
          />
        ))}
        {time !== null && time >= start && time <= end && (
          <div
            className="pointer-events-none absolute inset-y-0 w-0.5 bg-foreground"
            style={{ left: `${((time - start) / length) * 100}%` }}
          />
        )}
      </div>
      <p className="text-base leading-relaxed">
        {words.map((word, i) => {
          const lit = time !== null && time >= word.start;
          const current = lit && time !== null && time < word.end;
          return (
            <span
              key={i}
              className={cn(
                "rounded px-0.5 transition-colors",
                current
                  ? "bg-primary text-primary-foreground"
                  : lit
                    ? "text-primary"
                    : "text-muted-foreground",
              )}
            >
              {word.word}{" "}
            </span>
          );
        })}
      </p>
    </div>
  );
};

/** Both timings, following the playhead only while this line plays. */
const LiveTimings: React.FC<{
  moment: WordTimingMoment;
  experiment: WordTimingExperiment;
  playhead: Playhead;
  playing: boolean;
}> = ({ moment, experiment, playhead, playing }) => {
  const rows = (time: number | null) => (
    <div className="space-y-3">
      <TimingRow
        label={experiment.a.label}
        words={moment.a}
        start={moment.start}
        end={moment.end}
        time={time}
      />
      <TimingRow
        label={experiment.b.label}
        words={moment.b}
        start={moment.start}
        end={moment.end}
        time={time}
      />
    </div>
  );
  return playing ? (
    <FollowPlayhead playhead={playhead} render={rows} />
  ) : (
    rows(null)
  );
};

const FollowPlayhead: React.FC<{
  playhead: Playhead;
  render: (time: number) => React.ReactNode;
}> = ({ playhead, render }) => <>{render(usePlayheadTime(playhead))}</>;

const MomentRow: React.FC<{
  moment: WordTimingMoment;
  experiment: WordTimingExperiment;
  playhead: Playhead;
  playFrom: (seconds: number) => void;
  onAnswer: (answer: WordTimingAnswer | null) => void;
  saving: boolean;
  playing: boolean;
}> = ({
  moment,
  experiment,
  playhead,
  playFrom,
  onAnswer,
  saving,
  playing,
}) => {
  const shift =
    moment.meanShift !== null
      ? `words ${moment.meanShift.toFixed(1)} s apart on average`
      : "different words timed";

  return (
    <li
      className={cn(
        "space-y-3 rounded-md border px-3 py-2.5 transition-colors",
        playing ? "border-primary/60 bg-primary/10" : "border-border/60",
      )}
    >
      <div className="flex flex-wrap items-center gap-2">
        <Button
          size="sm"
          variant="outline"
          onClick={() => playFrom(moment.start - PLAY_BEFORE_SECONDS)}
        >
          <Play className="size-3.5" />
          Play {clock(moment.start)}
        </Button>
        <span className="min-w-0 flex-1 text-sm text-muted-foreground">
          {shift}
        </span>
        {moment.answer && (
          <Badge variant="secondary">
            <Check />
            Answered
          </Badge>
        )}
      </div>
      <LiveTimings
        moment={moment}
        experiment={experiment}
        playhead={playhead}
        playing={playing}
      />
      <ToggleGroup
        type="single"
        variant="outline"
        size="sm"
        value={moment.answer ?? ""}
        disabled={saving}
        // Pressing the chosen answer again clears it.
        onValueChange={(value) => onAnswer((value as WordTimingAnswer) || null)}
        aria-label="Which timing followed the singing"
        className="flex-wrap"
      >
        {answerOptions(experiment).map(({ answer, label }) => (
          <ToggleGroupItem key={answer} value={answer} className="px-3">
            {label}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
    </li>
  );
};

const SongDetail: React.FC<{
  row: WordTimingSongRow;
  experiment: WordTimingExperiment;
  selection: ReviewSelection;
  /** Called on every answer, so the list keeps this song while it's open. */
  onAnswered: () => void;
}> = ({ row, experiment, selection, onAnswered }) => {
  const {
    data: song,
    isLoading,
    error,
  } = useWordTimingSong(experiment.id, row.songId);
  const save = useSaveWordTimingAnswers(experiment.id, row.songId);
  const player = useRef<SongAudioPreviewHandle>(null);
  const playhead = usePlayhead();

  const playFrom = (seconds: number) =>
    player.current?.playFrom(Math.max(0, seconds));

  const moments = song?.moments ?? NO_MOMENTS;
  const activeKey = useActiveMoment(playhead, moments);
  const unanswered = moments.filter((m) => !m.answer);
  const score = (value: number | null) =>
    value === null ? "–" : value.toFixed(2);

  return (
    <div className="space-y-5">
      <SongSummary
        basics={{ id: row.songId, title: row.title, artist: row.artist }}
        size="sm"
      />
      <StemPreview
        songId={row.songId}
        onTimeChange={playhead.set}
        playerRef={player}
      />
      <dl className="grid grid-cols-[auto_auto_auto] justify-start gap-x-6 gap-y-1 text-sm">
        <dt />
        <dd className="font-medium text-muted-foreground">Bad lines</dd>
        <dd className="font-medium text-muted-foreground">Score</dd>
        {[experiment.a, experiment.b].map((side, i) => {
          const summary = i === 0 ? row.a : row.b;
          return (
            <React.Fragment key={side.key}>
              <dt className="text-muted-foreground">{side.label}</dt>
              <dd className="tabular-nums">
                {summary.bad ?? "–"} of {summary.lines ?? "–"}
              </dd>
              <dd className="tabular-nums">{score(summary.meanScore)}</dd>
            </React.Fragment>
          );
        })}
      </dl>

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
        <section className="space-y-3">
          <h3 className="font-semibold">Lines that differ</h3>
          {moments.length > 0 && unanswered.length === 0 && (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-success/40 bg-success/10 px-3 py-2">
              <p className="text-sm">All checked. Thanks!</p>
              <Button size="sm" onClick={selection.done}>
                Next song
              </Button>
            </div>
          )}
          {moments.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              The two timings agree on every line.
            </p>
          ) : (
            <ol className="space-y-2">
              {moments.map((moment) => (
                <MomentRow
                  key={moment.key}
                  moment={moment}
                  experiment={experiment}
                  playhead={playhead}
                  playFrom={playFrom}
                  saving={save.isPending}
                  playing={moment.key === activeKey}
                  onAnswer={(answer) => {
                    onAnswered();
                    save.mutate({ answers: [{ key: moment.key, answer }] });
                  }}
                />
              ))}
            </ol>
          )}
        </section>
      )}
    </div>
  );
};

/**
 * Two experimental word timings of the same songs, side by side, for saying
 * by ear which follows the singing. An experiment script writes the timings
 * to a folder on the machine it ran on; nothing here reaches the TV.
 */
const AdminCompareWordTimingPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const experiments = useWordTimingExperiments();
  const list = experiments.data?.experiments ?? [];
  const experimentId =
    list.find((e) => e.id === searchParams.get(EXPERIMENT_PARAM))?.id ??
    list[list.length - 1]?.id;
  const { data, isLoading, error } = useWordTimingSongs(experimentId);
  const [filter, setFilter] = useState("to-check");
  // A song stays listed while it's open, even once it's checked, so the
  // list doesn't jump while you're still listening.
  const [pinned, setPinned] = useState<string | null>(null);
  const selectedId = searchParams.get("song");
  const keep = pinned && (selectedId === null || selectedId === pinned);

  const experiment = data?.experiment;
  const songs = data?.songs;
  const tally = data?.tally ?? {};
  const answered = Object.values(tally).reduce((sum, n) => sum + (n ?? 0), 0);

  const matches = (row: WordTimingSongRow) => {
    if (filter === "to-check") return row.moments > 0 && !isDone(row);
    if (filter === "checked") return row.answered > 0;
    if (filter === "all") return true;
    return row.group === filter;
  };
  const shown = songs?.filter((row) => matches(row) || row.songId === keep);

  const chooseExperiment = (id: string) => {
    const next = new URLSearchParams(searchParams);
    next.set(EXPERIMENT_PARAM, id);
    next.delete("song");
    setSearchParams(next);
  };

  return (
    <ReviewLayout
      label="Songs to compare word timing on"
      items={experiments.isLoading ? undefined : experimentId ? shown : []}
      getId={(row) => row.songId}
      isLoading={experiments.isLoading || isLoading}
      error={experiments.error ?? error}
      toolbar={
        <div className="space-y-3">
          {list.length > 1 && (
            <ToggleGroup
              type="single"
              variant="outline"
              size="sm"
              value={experimentId ?? ""}
              onValueChange={(value) => value && chooseExperiment(value)}
              aria-label="Which experiment"
              className="flex-wrap"
            >
              {list.map((e) => (
                <ToggleGroupItem key={e.id} value={e.id} className="px-3">
                  {e.name}
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
          )}
          {experiment && (
            <p className="text-sm text-muted-foreground">
              <span className="font-medium text-foreground">
                {experiment.name}.
              </span>{" "}
              {experiment.description} Each song lists the lines where the two
              timings differ. Press play, watch both light up, and say which
              follows the singer.
            </p>
          )}
          {experiment && answered > 0 && (
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
              <span className="font-medium">
                Your answers so far ({answered}):
              </span>
              {answerOptions(experiment)
                .filter(({ answer }) => tally[answer])
                .map(({ answer, label }) => (
                  <span key={answer} className="text-muted-foreground">
                    {label}{" "}
                    <span className="font-medium tabular-nums text-foreground">
                      {tally[answer]}
                    </span>
                  </span>
                ))}
            </div>
          )}
        </div>
      }
      filters={
        experiment &&
        !!songs?.length && (
          <FilterChips
            label="Show songs"
            value={filter}
            onChange={setFilter}
            chips={[
              {
                value: "to-check",
                label: "To check",
                count: songs.filter((r) => r.moments > 0 && !isDone(r)).length,
              },
              {
                value: "checked",
                label: "Checked",
                count: songs.filter((r) => r.answered > 0).length,
              },
              ...experiment.groups.map((group) => ({
                value: group.key,
                label: group.label,
                count: songs.filter((r) => r.group === group.key).length,
              })),
              { value: "all", label: "All", count: songs.length },
            ]}
          />
        )
      }
      empty={
        <ReviewEmpty
          icon={FlaskConical}
          title={
            experimentId ? "No songs here" : "No experiments on this machine"
          }
        >
          {experimentId
            ? "Try another filter."
            : "Experiment scripts such as align_on_mix.py write their results to a folder on the machine that runs them. Run one here first."}
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
      renderDetail={(row, selection) =>
        experiment && (
          <SongDetail
            row={row}
            experiment={experiment}
            selection={{
              ...selection,
              done: () => {
                setPinned(null);
                selection.done();
              },
            }}
            onAnswered={() => setPinned(row.songId)}
          />
        )
      }
    />
  );
};

export default AdminCompareWordTimingPage;
