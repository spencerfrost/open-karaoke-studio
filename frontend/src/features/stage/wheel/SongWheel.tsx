/**
 * SongWheel - song select as a DDR-style wheel: Letter → Artist → Song.
 *
 * Built for the four keys a numpad on a mic stand will have (arrows, Enter,
 * Back), with the mouse still first-class: its scroll wheel spins the column
 * under the pointer. An accordion of ~600 artists cannot be driven by
 * up/down/enter/back; this can.
 *
 * The three columns sit on a cylinder whose axis is behind the middle of the
 * screen. Left/Right turns it. Each column rides the cylinder and then turns
 * back by its own angle, so text always faces the room - side columns read as
 * further away, never tilted.
 *
 * Everything is laid out on a fixed 1600×900 frame and scaled to fit, so the
 * wheel looks the same on the TV as on a laptop, and the tuning numbers in
 * wheelModel mean the same thing everywhere.
 *
 * Artwork (the artist photo in the songs heading, the song card, the blurred
 * backdrop) follows the *settled* cursor only; see
 * docs/plans/2026-09-25-stage-wheel-artwork.md.
 *
 * See docs/plans/2026-09-25-stage-song-wheel.md.
 */

import React, { useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, useReducedMotion } from "framer-motion";
import { Loader2, Theater } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Song } from "@/types/Song";
import SongInfoCard from "./SongInfoCard";
import WheelArtwork from "./WheelArtwork";
import WheelColumn from "./WheelColumn";
import { useSongWheel, type WheelFocusRequest } from "./useSongWheel";
import { useWheelKeys } from "./useWheelKeys";
import {
  COLUMN,
  COLUMN_WIDTHS,
  LETTERS,
  ROW_HEIGHTS,
  WHEEL_TUNING,
  artistImageUrl,
  columnBrightness,
  columnSeats,
  songHeroSources,
  tileInitial,
  type ColumnIndex,
} from "./wheelModel";

const FRAME_W = 1600;
const FRAME_H = 900;
const SEATS = columnSeats();
/** Where each column's list starts, below its header (the songs heading has
 *  the artist photo in it). */
const LIST_TOP = [60, 60, 128] as const;
/** The ring's area on the frame; the song card centres on it. */
const STAGE_TOP = 110;
const STAGE_BOTTOM = 120;
/**
 * The full-screen blurred backdrop. The one artwork piece that can go without
 * touching the others: switch it off here if it stutters or looks wrong on
 * the TV.
 */
const SHOW_BACKDROP = true;

interface SongWheelProps {
  /** Keys are live only while song select is the screen showing. */
  active: boolean;
  focusArtist?: WheelFocusRequest;
  onPickSong: (song: Song) => void;
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

const Kbd: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <kbd className="inline-grid h-[38px] min-w-[42px] place-items-center rounded-lg border border-b-[3px] border-border bg-surface px-2.5 font-display text-xl font-bold text-foreground">
    {children}
  </kbd>
);

const SongWheel: React.FC<SongWheelProps> = ({
  active,
  focusArtist,
  onPickSong,
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
    onLeave: () => onLeave?.(),
  });

  useWheelKeys({
    enabled: active,
    onScrollMs: setHeldScrollMs,
    move: wheel.move,
    turn: wheel.turn,
    enter: wheel.enter,
    back: wheel.back,
  });

  const turnMs = reducedMotion ? 0 : WHEEL_TUNING.turnMs;
  const scrollMs = reducedMotion ? 0 : (heldScrollMs ?? WHEEL_TUNING.scrollMs);

  // Pull the ring back by its radius so the front column sits at z=0 (true
  // size), then turn it so the active column faces the room.
  const { radiusPx } = WHEEL_TUNING;
  const ringAngle = -SEATS[wheel.col];
  const columnTransform = (i: ColumnIndex) =>
    `rotateY(${SEATS[i]}deg) translateZ(${radiusPx}px) rotateY(${-(SEATS[i] + ringAngle)}deg)`;

  const { artist, songs, col, settledArtist, settledSong } = wheel;
  const settledArtistImage = settledArtist
    ? artistImageUrl(settledArtist)
    : null;
  const songInFront = col === COLUMN.song && settledSong !== null;
  const backdropSources =
    songInFront && settledSong
      ? songHeroSources(settledSong)
      : [settledArtistImage];

  const legend: [string[], string][] = [
    [["▲", "▼"], ["Jump letter", "Browse artists", "Browse songs"][col]],
    [["◀", "▶"], "Change column"],
    [["⏎"], ["Go to artists", "See songs", "Pick song"][col]],
  ];
  if (col === COLUMN.song) legend.push([["⌫"], "Back to artists"]);
  else if (onLeave) legend.push([["⌫"], "Back to the song"]);

  const shared = (i: ColumnIndex) => ({
    width: COLUMN_WIDTHS[i],
    rowHeight: ROW_HEIGHTS[i],
    listTop: LIST_TOP[i],
    active: col === i,
    brightness: columnBrightness(Math.abs(i - col)),
    transform: columnTransform(i),
    turnMs,
    scrollMs,
    onActivate: () => wheel.focusColumn(i),
    onRowClick: (index: number) => wheel.pickRow(i, index),
    onWheelSteps: (dir: -1 | 1, steps: number) =>
      wheel.scrollColumn(i, dir, steps),
  });

  let body: React.ReactNode;
  if (wheel.isLoading) {
    body = (
      <div className="absolute inset-0 flex items-center justify-center gap-4 text-3xl text-foreground/60">
        <Loader2 className="size-9 animate-spin" />
        Loading the library…
      </div>
    );
  } else if (wheel.error) {
    body = (
      <div className="absolute inset-0 flex items-center justify-center text-3xl text-destructive">
        Couldn't load the library.
      </div>
    );
  } else if (wheel.artists.length === 0) {
    body = (
      <div className="absolute inset-0 flex items-center justify-center text-3xl text-foreground/60">
        No songs yet. Add one with the + button.
      </div>
    );
  } else {
    body = (
      <>
        <div className="absolute inset-x-16 top-10 flex items-baseline gap-3.5 overflow-hidden whitespace-nowrap font-display text-3xl font-bold uppercase tracking-[0.04em] text-foreground/60">
          <span>Artists</span>
          <span className="text-foreground/30">▸</span>
          <b className="font-extrabold text-foreground">
            {LETTERS[wheel.letterIndex]}
          </b>
          {col >= COLUMN.artist && artist && (
            <>
              <span className="text-foreground/30">▸</span>
              <b className="truncate font-extrabold text-foreground">
                {artist.name}
              </b>
            </>
          )}
        </div>

        <div
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
            style={{
              transformStyle: "preserve-3d",
              transform: `translateZ(${-radiusPx}px) rotateY(${ringAngle}deg)`,
              transition: `transform ${turnMs}ms ${WHEEL_TUNING.turnEasing}`,
            }}
          >
            <WheelColumn
              {...shared(COLUMN.letter)}
              label="A–Z"
              count={LETTERS.length}
              cursor={wheel.letterIndex}
              isRowDisabled={(i) => wheel.firstByLetter[i] === -1}
              rowClassName="justify-center font-display text-5xl font-extrabold"
              renderRow={(i) => LETTERS[i]}
            />

            <WheelColumn
              {...shared(COLUMN.artist)}
              label="Artists"
              count={wheel.artists.length}
              cursor={wheel.artistIndex}
              rowClassName="px-7 text-[32px]"
              renderRow={(i) => {
                const a = wheel.artists[i];
                return (
                  <>
                    <span className="truncate">{a.name}</span>
                    <span className="ml-auto flex flex-none items-center gap-2 pl-4 font-display text-[22px] tabular-nums text-foreground/40">
                      {a.isShow && (
                        <Theater className="size-5" aria-label="Show" />
                      )}
                      {a.songCount}
                    </span>
                  </>
                );
              }}
            />

            <WheelColumn
              {...shared(COLUMN.song)}
              label="Songs"
              header={
                <div className="flex items-center gap-[18px]">
                  {/* Follows the settled artist and dims while the cursor
                      moves, so it never claims a photo for the wrong name. */}
                  <WheelArtwork
                    shape="round"
                    sources={[settledArtistImage]}
                    fallback={
                      settledArtist
                        ? tileInitial(settledArtist.name)
                        : undefined
                    }
                    className={cn(
                      "size-[84px] flex-none shadow-[0_8px_30px_rgba(0,0,0,.45)]",
                      !reducedMotion && "transition-opacity duration-200",
                      wheel.artistPending && "opacity-25",
                    )}
                  />
                  <div className="min-w-0">
                    Songs
                    <span className="mt-0.5 block truncate text-[40px] font-extrabold normal-case tracking-[0.02em] text-foreground">
                      {artist?.name}
                    </span>
                  </div>
                </div>
              }
              count={songs.length}
              cursor={wheel.songIndex}
              placeholder={
                wheel.songsLoading ? (
                  <Loader2 className="size-7 animate-spin" />
                ) : (
                  "No songs"
                )
              }
              isRowDisabled={(i) => songs[i]?.status !== "processed"}
              rowClassName="px-7 text-[32px]"
              renderRow={(i) => {
                const song = songs[i];
                return (
                  <>
                    <span className="w-11 flex-none font-display text-[22px] tabular-nums text-foreground/40">
                      {i + 1}
                    </span>
                    <span className="truncate">{song.title}</span>
                    {song.status !== "processed" && (
                      <span className="ml-auto flex-none pl-4 font-display text-[20px] uppercase tracking-wider text-foreground/40">
                        Processing
                      </span>
                    )}
                  </>
                );
              }}
            />
          </div>
        </div>

        <AnimatePresence>
          {active && songInFront && settledSong && (
            <SongInfoCard
              key="song-info"
              song={settledSong}
              pending={wheel.songPending}
              centerY={(STAGE_TOP + FRAME_H - STAGE_BOTTOM) / 2}
            />
          )}
        </AnimatePresence>

        <div className="absolute inset-x-0 bottom-11 flex justify-center gap-11 text-[22px] text-foreground/60">
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
