/**
 * SongWheel - song select as a DDR-style wheel: a list of sources, then the
 * source's own columns (Artists A–Z: Letter → Artist → Song; Recently added:
 * one list of songs).
 *
 * Built for the four keys a numpad on a mic stand will have (arrows, Enter,
 * Back), with the mouse still first-class: its scroll wheel spins the column
 * under the pointer. An accordion of ~600 artists cannot be driven by
 * up/down/enter/back; this can.
 *
 * The columns sit on a cylinder whose axis is behind the middle of the
 * screen. Left/Right turns it. Each column rides the cylinder and then turns
 * back by its own angle, so text always faces the room - side columns read as
 * further away, never tilted.
 *
 * Everything is laid out on a fixed 1600×900 frame and scaled to fit, so the
 * wheel looks the same on the TV as on a laptop, and the tuning numbers in
 * wheelModel mean the same thing everywhere.
 *
 * Artwork (the artist photo in the songs heading, the song card, the blurred
 * backdrop) follows the *settled* cursor only.
 */

import React, { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, useReducedMotion } from "framer-motion";
import { Loader2, Plus, Search, Theater } from "lucide-react";
import type { Song } from "@/types/Song";
import { artistSongTotal } from "@/hooks/api/useArtists";
import SongInfoCard from "./SongInfoCard";
import WheelArtwork from "./WheelArtwork";
import WheelColumn from "./WheelColumn";
import { useSongWheel, type WheelFocusRequest } from "./useSongWheel";
import { useWheelKeys } from "./useWheelKeys";
import { useWheelPreview } from "./useWheelPreview";
import {
  COLUMN_LEGEND,
  COLUMN_SPECS,
  LETTERS,
  SOURCES,
  SOURCE_ACTIONS,
  WHEEL_TUNING,
  artistImageUrl,
  primaryArtists,
  columnBrightness,
  columnIndexOf,
  columnSeats,
  isColumnHidden,
  ringAngleFor,
  routeWheelScroll,
  songByline,
  songHeroSources,
  tileInitial,
  type ColumnKind,
  type SourceId,
  type WheelArtist,
  type WheelScrollLock,
} from "./wheelModel";

const FRAME_W = 1600;
const FRAME_H = 900;
const SEATS_BY_SOURCE = Object.fromEntries(
  SOURCES.map((source) => [source.id, columnSeats(source.columns)]),
) as Record<SourceId, number[]>;
/** The ring's area on the frame; the song card centres on it. */
const STAGE_TOP = 110;
const STAGE_BOTTOM = 120;
/**
 * The full-screen blurred backdrop. The one artwork piece that can go without
 * touching the others: switch it off here if it stutters or looks wrong on
 * the TV.
 */
const SHOW_BACKDROP = true;
/** One notch of a line-based mouse wheel, or this many pixels of a smooth one. */
const WHEEL_PIXELS_PER_ROW = 50;

interface SongWheelProps {
  /** Keys are live only while song select is the screen showing. */
  active: boolean;
  focusArtist?: WheelFocusRequest;
  onPickSong: (song: Song) => void;
  /** The source column's "Add a song" row. */
  onAddSong: () => void;
  /** The song column's last row: the add flow, on this artist. */
  onFindMore: (artist: WheelArtist) => void;
  /** Back from the letter or artist column; null when there is nowhere to go. */
  onLeave: (() => void) | null;
  /**
   * Where the blurred backdrop is drawn: a layer behind the whole screen, top
   * bar included, which the wheel's own box doesn't reach. No backdrop until
   * it exists.
   */
  backdropTarget?: HTMLElement | null;
}

/** Scale the fixed frame to fit its container, letterboxed. */
function useFitScale(ref: React.RefObject<HTMLDivElement | null>) {
  const [scale, setScale] = useState(1);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const fit = () =>
      setScale(Math.min(el.clientWidth / FRAME_W, el.clientHeight / FRAME_H));
    fit();
    const observer = new ResizeObserver(fit);
    observer.observe(el);
    return () => observer.disconnect();
  }, [ref]);
  return scale;
}

/**
 * The mouse wheel, for the whole wheel rather than per column: a flick that
 * starts over a column keeps scrolling it after the ring turns it out from
 * under the pointer, even when the pointer is left over empty space (see
 * routeWheelScroll). Native, because React's onWheel is passive and cannot
 * stop the page scrolling.
 */
function useMouseWheel(
  ref: React.RefObject<HTMLDivElement | null>,
  scrollColumn: (col: number, dir: -1 | 1, steps: number) => void,
) {
  const latest = useRef(scrollColumn);
  latest.current = scrollColumn;
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let lock: WheelScrollLock | null = null;
    let acc = 0;
    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      const over = (e.target as Element | null)?.closest<HTMLElement>(
        "[data-wheel-column]",
      );
      const hovered = over ? Number(over.dataset.wheelColumn) : null;
      const route = routeWheelScroll(lock, hovered, performance.now());
      lock = route.lock;
      if (route.target === null) return;
      if (route.started) acc = 0;

      const step =
        e.deltaMode === WheelEvent.DOM_DELTA_LINE ? 1 : WHEEL_PIXELS_PER_ROW;
      acc += e.deltaY;
      const steps = Math.trunc(acc / step);
      if (steps === 0) return;
      acc -= steps * step;
      latest.current(route.target, steps < 0 ? -1 : 1, Math.abs(steps));
    };
    el.addEventListener("wheel", handleWheel, { passive: false });
    return () => el.removeEventListener("wheel", handleWheel);
  }, [ref]);
}

const Kbd: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <kbd className="inline-grid h-[38px] min-w-[42px] place-items-center rounded-lg border border-b-[3px] border-border bg-surface px-2.5 font-display text-xl font-bold text-foreground">
    {children}
  </kbd>
);

const SongWheel: React.FC<SongWheelProps> = ({
  active,
  focusArtist,
  onPickSong,
  onAddSong,
  onFindMore,
  onLeave,
  backdropTarget,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const scale = useFitScale(containerRef);
  const reducedMotion = useReducedMotion() ?? false;
  const [heldScrollMs, setHeldScrollMs] = useState<number | null>(null);

  const wheel = useSongWheel({
    focusArtist,
    onPickSong,
    // The only action so far.
    onAction: onAddSong,
    onLeave: () => onLeave?.(),
    onFindMore,
  });

  useMouseWheel(containerRef, wheel.scrollColumn);

  useWheelKeys({
    enabled: active,
    onScrollMs: setHeldScrollMs,
    move: wheel.move,
    turn: wheel.turn,
    enter: wheel.enter,
    back: wheel.back,
    leave: () => onLeave?.(),
  });

  const turnMs = reducedMotion ? 0 : WHEEL_TUNING.turnMs;
  const scrollMs = reducedMotion ? 0 : (heldScrollMs ?? WHEEL_TUNING.scrollMs);

  const { source, columns, col, az, recent, settledSong } = wheel;
  const kinds = source.columns;
  const frontKind = kinds[col];
  const seats = SEATS_BY_SOURCE[source.id];

  // Pull the ring back by its radius so the front column sits at z=0 (true
  // size), then turn it so the active column faces the room - except the
  // source and letter columns, which grow where they are (see ringAngleFor).
  //
  // The ring is in each column's own transform rather than on a parent
  // element: Chrome hit-tests a 3D child through its parent's plane, and with
  // the ring turned near edge-on (the song column in front), clicks on the
  // left-hand columns never reached them.
  const { radiusPx } = WHEEL_TUNING;
  const ringAngle = ringAngleFor(col, seats, kinds);
  const columnTransform = (i: number) => {
    const ring = `translateZ(${-radiusPx}px) rotateY(${ringAngle}deg)`;
    const seat = `${ring} rotateY(${seats[i]}deg) translateZ(${radiusPx}px) rotateY(${-(seats[i] + ringAngle)}deg)`;
    const grow = i === col && !!COLUMN_SPECS[kinds[i]].staysPut;
    return `${seat} scale(${grow ? WHEEL_TUNING.inPlaceActiveScale : 1})`;
  };

  const settledArtistImage = az.settledArtist
    ? artistImageUrl(az.settledArtist)
    : null;
  const songInFront =
    (frontKind === "song" || frontKind === "recent") && settledSong !== null;
  useWheelPreview(
    active && songInFront && !wheel.songPending ? settledSong : null,
  );
  // The artist photo only stands for the A–Z lists; Recently added has no
  // artist to show until a song rests under the cursor.
  const backdropSources =
    songInFront && settledSong
      ? songHeroSources(settledSong)
      : [source.id === "az" ? settledArtistImage : null];

  const legendText = COLUMN_LEGEND[frontKind];
  const legend: [string[], string][] = [
    [["▲", "▼"], legendText.move],
    [["◀", "▶"], "Change column"],
    [
      ["⏎"],
      (frontKind === "source" &&
        SOURCE_ACTIONS.find((a) => a.id === wheel.sourceAction)?.label) ||
        (frontKind === "song" && az.onFindMore && "Find more") ||
        legendText.enter,
    ],
  ];
  if (frontKind === "song") legend.push([["⌫"], "Back to artists"]);
  else if (onLeave) legend.push([["⌫"], "Back to the song"]);

  const shared = (i: number) => {
    const kind = kinds[i];
    const spec = COLUMN_SPECS[kind];
    const steps = Math.abs(i - col);
    return {
      key: `${source.id}:${kind}`,
      width: spec.width,
      rowHeight: spec.rowHeight,
      listTop: spec.listTop,
      active: col === i,
      // A narrow column turns in behind the ones in front of it and would show
      // through them, so far-back columns are not drawn.
      brightness: isColumnHidden(kind, steps) ? 0 : columnBrightness(steps),
      transform: columnTransform(i),
      turnMs,
      scrollMs,
      onActivate: () => wheel.focusColumn(i),
      onRowClick: (index: number) => wheel.pickRow(i, index),
      column: i,
      count: columns[i].count,
      cursor: columns[i].cursor,
    };
  };

  const processingTag = (
    <span className="ml-auto flex-none pl-4 font-display text-[20px] uppercase tracking-wider text-foreground-faint">
      Processing
    </span>
  );

  const renderColumn = (kind: ColumnKind, i: number) => {
    switch (kind) {
      case "source":
        return (
          <WheelColumn
            {...shared(i)}
            // Lists and actions both, so no heading over them.
            label="Lists"
            labelHidden
            rowClassName="px-6 text-[28px]"
            renderRow={(row) =>
              row < SOURCES.length ? (
                <span className="truncate">{SOURCES[row].label}</span>
              ) : (
                <>
                  <Plus className="mr-3 size-7 flex-none text-accent" />
                  <span className="truncate">
                    {SOURCE_ACTIONS[row - SOURCES.length].label}
                  </span>
                </>
              )
            }
          />
        );

      case "letter":
        return (
          <WheelColumn
            {...shared(i)}
            label="A–Z"
            isRowDisabled={(row) => az.firstByLetter[row] === -1}
            rowClassName="justify-center font-display text-5xl font-extrabold"
            renderRow={(row) => LETTERS[row]}
          />
        );

      case "artist":
        return (
          <WheelColumn
            {...shared(i)}
            label="Artists"
            rowClassName="px-7 text-[32px]"
            renderRow={(row) => {
              const a = az.artists[row];
              return (
                <>
                  <span className="truncate">{a.name}</span>
                  <span className="ml-auto flex flex-none items-center gap-2 pl-4 font-display text-[22px] tabular-nums text-foreground-faint">
                    {a.isShow && (
                      <Theater className="size-5" aria-label="Show" />
                    )}
                    {artistSongTotal(a)}
                  </span>
                </>
              );
            }}
          />
        );

      case "song":
        return (
          <WheelColumn
            {...shared(i)}
            label="Songs"
            header={
              <div className="flex items-center gap-[18px]">
                {/* Follows the settled artist and dims while the cursor
                    moves, so it never claims a photo for the wrong name. */}
                <WheelArtwork
                  shape="round"
                  sources={[settledArtistImage]}
                  fallback={
                    az.settledArtist
                      ? tileInitial(az.settledArtist.name)
                      : undefined
                  }
                  pending={az.artistPending}
                  staleOpacity={0.25}
                  className="size-[84px] flex-none shadow-[0_8px_30px_rgba(0,0,0,.45)]"
                />
                <div className="min-w-0">
                  Songs
                  <span className="mt-0.5 block truncate text-[40px] font-extrabold normal-case tracking-[0.02em] text-foreground">
                    {az.artist?.name}
                  </span>
                </div>
              </div>
            }
            placeholder={
              az.songsLoading ? (
                <Loader2 className="size-7 animate-spin" />
              ) : (
                "No songs"
              )
            }
            isRowDisabled={(row) =>
              row < az.songs.length && az.songs[row].status !== "processed"
            }
            rowClassName="px-7 text-[32px]"
            renderRow={(row) => {
              const song = az.songs[row];
              // The songbook's "Find more from …" card, as the last row:
              // songs not in the songbook yet, on the add screen.
              if (!song) {
                return (
                  <>
                    <Search className="mr-3 size-7 flex-none text-accent" />
                    <span className="truncate">
                      Find more from {az.artist?.name}
                    </span>
                  </>
                );
              }
              return (
                <>
                  <span className="w-11 flex-none font-display text-[22px] tabular-nums text-foreground-faint">
                    {row + 1}
                  </span>
                  <span className="truncate">{song.title}</span>
                  {/* A song they guest on says whose it is */}
                  {song.role === "featured" && (
                    <span className="flex-none truncate pl-4 text-[24px] text-foreground-faint">
                      {primaryArtists(song)}
                    </span>
                  )}
                  {song.status !== "processed" && processingTag}
                </>
              );
            }}
          />
        );

      case "recent":
        return (
          <WheelColumn
            {...shared(i)}
            label="Recently added"
            placeholder={
              recent.isLoading ? (
                <Loader2 className="size-7 animate-spin" />
              ) : (
                "No songs yet"
              )
            }
            isRowDisabled={(row) => recent.songs[row]?.status !== "processed"}
            rowClassName="px-7"
            renderRow={(row) => {
              const song = recent.songs[row];
              return (
                <>
                  <div className="min-w-0 flex-1 leading-tight">
                    <span className="block truncate text-[32px]">
                      {song.title}
                    </span>
                    <span className="block truncate text-[22px] font-normal text-foreground-faint">
                      {songByline(song)}
                    </span>
                  </div>
                  {song.status !== "processed" && processingTag}
                </>
              );
            }}
          />
        );
    }
  };

  const artistColumn = columnIndexOf(source, "artist");

  let body: React.ReactNode;
  if (source.id === "az" && az.isLoading) {
    body = (
      <div className="absolute inset-0 flex items-center justify-center gap-4 text-3xl text-foreground-dim">
        <Loader2 className="size-9 animate-spin" />
        Loading the songbook…
      </div>
    );
  } else if (source.id === "az" && az.error) {
    body = (
      <div className="absolute inset-0 flex items-center justify-center text-3xl text-destructive">
        Couldn't load the songbook.
      </div>
    );
  } else if (source.id === "az" && az.artists.length === 0) {
    body = (
      <div className="absolute inset-0 flex items-center justify-center text-3xl text-foreground-dim">
        No songs yet. Press Add a song, up top, to add one.
      </div>
    );
  } else {
    body = (
      <>
        <div className="absolute inset-x-16 top-10 flex items-baseline gap-3.5 overflow-hidden whitespace-nowrap font-display text-3xl font-bold uppercase tracking-[0.04em] text-foreground-dim">
          {/* The way back to the list of sources for the mouse, which can't
              ◀ its way there. */}
          <button
            type="button"
            onClick={() => wheel.focusColumn(0)}
            className={
              col === 0
                ? "font-extrabold uppercase text-foreground"
                : "uppercase hover:text-foreground"
            }
          >
            {source.label}
          </button>
          {source.id === "az" && (
            <>
              <span className="text-foreground-faint">▸</span>
              <b className="font-extrabold text-foreground">
                {LETTERS[az.letterIndex]}
              </b>
              {col >= artistColumn && az.artist && (
                <>
                  <span className="text-foreground-faint">▸</span>
                  <b className="truncate font-extrabold text-foreground">
                    {az.artist.name}
                  </b>
                </>
              )}
            </>
          )}
        </div>

        <div
          data-tour="song-wheel"
          className="absolute inset-x-0"
          style={{
            top: STAGE_TOP,
            bottom: STAGE_BOTTOM,
            perspective: 1700,
            perspectiveOrigin: "50% 50%",
          }}
        >
          <div
            className="absolute left-1/2 top-1/2 size-0"
            style={{ transformStyle: "preserve-3d" }}
          >
            {kinds.map((kind, i) => (
              <React.Fragment key={`${source.id}:${kind}`}>
                {renderColumn(kind, i)}
              </React.Fragment>
            ))}
          </div>
        </div>

        <AnimatePresence>
          {active && songInFront && settledSong && (
            <SongInfoCard
              key="song-info"
              song={settledSong}
              pending={wheel.songPending}
              onPick={wheel.enter}
              centerY={(STAGE_TOP + FRAME_H - STAGE_BOTTOM) / 2}
            />
          )}
        </AnimatePresence>

        <div className="absolute inset-x-0 bottom-11 flex justify-center gap-11 text-[22px] text-foreground-dim">
          {legend.map(([keys, text]) => (
            <div key={text} className="flex items-center gap-3">
              {keys.map((k) => (
                <Kbd key={k}>{k}</Kbd>
              ))}
              <span>{text}</span>
            </div>
          ))}
        </div>
      </>
    );
  }

  return (
    <div ref={containerRef} className="relative h-full w-full overflow-hidden">
      {SHOW_BACKDROP &&
        backdropTarget &&
        createPortal(
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 overflow-hidden"
          >
            <WheelArtwork
              sources={backdropSources}
              className="absolute -inset-[15%] rounded-none opacity-50"
              layerClassName="blur-[90px] saturate-[1.2]"
              fadeMs={600}
            />
            {/* Keeps the middle dark enough for the text. */}
            <div className="wheel-backdrop-shade absolute inset-0" />
          </div>,
          backdropTarget,
        )}
      <div
        className="absolute left-1/2 top-1/2"
        style={{
          width: FRAME_W,
          height: FRAME_H,
          transform: `translate(-50%, -50%) scale(${scale})`,
        }}
      >
        {body}
      </div>
    </div>
  );
};

export default SongWheel;
