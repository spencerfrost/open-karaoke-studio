/**
 * SongInfoCard - what the song under the cursor is, on the right of the wheel.
 *
 * Shown only while the song column is at the front: the one time the right of
 * the screen is empty. It sits on the wheel's flat frame, beside the cylinder
 * rather than on it, so the ring's 3D transforms never touch it.
 *
 * Built around what the library actually has (see the coverage table in
 * docs/plans/2026-09-25-stage-wheel-artwork.md): the video still leads because
 * most songs have one, and any fact a song lacks is left out rather than shown
 * as "—", so a sparse song gets a shorter card, not a card of blanks.
 */

import React from "react";
import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";
import type { Song } from "@/types/Song";
import { formatTime } from "@/utils/formatters";
import WheelArtwork from "./WheelArtwork";
import {
  lyricsKind,
  songByline,
  songHeroSources,
  songYear,
  tileInitial,
  vocalRange,
  type LyricsKind,
} from "./wheelModel";

interface SongInfoCardProps {
  /** The song the cursor last settled on. */
  song: Song;
  /** The cursor has moved on and not settled yet: the card is out of date. */
  pending: boolean;
  /** Frame pixels from the top to the card's centre line. */
  centerY: number;
}

const LYRICS_TAG: Record<LyricsKind, [string, TagTone]> = {
  "word-synced": ["Word-synced", "normal"],
  synced: ["Synced", "normal"],
  plain: ["Plain lyrics", "quiet"],
  none: ["No lyrics", "quiet"],
};

type TagTone = "normal" | "warn" | "quiet";

const Tag: React.FC<{ tone: TagTone; children: React.ReactNode }> = ({
  tone,
  children,
}) => (
  <span
    className={cn(
      "rounded-full px-3 py-1 font-display text-base font-bold uppercase tracking-[0.08em]",
      tone === "normal" && "bg-primary/15 text-primary",
      tone === "warn" && "bg-accent/20 text-accent",
      tone === "quiet" && "bg-foreground/10 text-foreground/60",
    )}
  >
    {children}
  </span>
);

const SongInfoCard: React.FC<SongInfoCardProps> = ({
  song,
  pending,
  centerY,
}) => {
  const reducedMotion = useReducedMotion() ?? false;
  const slide = reducedMotion ? 0 : 24;
  const ms = reducedMotion ? 0 : 220;

  const hasStill = !!(song.thumbnail || song.videoId);
  // Without a still the cover is the hero; an inset would repeat it.
  const showCover = hasStill && !!song.albumCoverUrl;

  const facts: [string, string][] = [];
  if (song.duration) facts.push(["Length", formatTime(song.duration)]);
  const range = vocalRange(song);
  if (range) facts.push(["Range", range]);
  const year = songYear(song);
  if (year) facts.push(["Year", String(year)]);

  const [lyricsLabel, lyricsTone] = LYRICS_TAG[lyricsKind(song)];

  return (
    <motion.aside
      aria-label="Song details"
      className="pointer-events-none absolute right-14 w-[400px] rounded-[20px] bg-surface/95 p-6 shadow-[0_20px_60px_rgba(0,0,0,.5)] ring-1 ring-border/30"
      style={{ top: centerY, y: "-50%" }}
      initial={{ opacity: 0, x: slide }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: slide }}
      // The ring's turn easing, so the card arrives with the column.
      transition={{ duration: ms / 1000, ease: [0.2, 0.8, 0.25, 1] }}
    >
      <div
        style={{
          opacity: pending ? 0.35 : 1,
          transition: `opacity ${reducedMotion ? 0 : 120}ms`,
        }}
      >
        <div className={cn("relative", showCover ? "mb-16" : "mb-5")}>
          <WheelArtwork
            sources={songHeroSources(song)}
            fallback={tileInitial(song.title)}
            className="aspect-video w-full shadow-[0_8px_30px_rgba(0,0,0,.45)]"
          />
          {showCover && (
            <WheelArtwork
              sources={[song.albumCoverUrl]}
              fallback={tileInitial(song.album || song.title)}
              className="absolute -bottom-12 left-[18px] size-[116px] shadow-[0_10px_30px_rgba(0,0,0,.5)] ring-4 ring-surface"
            />
          )}
        </div>

        <h3 className="line-clamp-2 text-balance font-display text-[40px] font-extrabold leading-[1.05] text-foreground">
          {song.title}
        </h3>
        <div className="mt-1 truncate text-2xl text-foreground/85">
          {songByline(song)}
        </div>
        {song.album && (
          <div className="mt-0.5 truncate text-xl text-foreground/60">
            {song.album}
          </div>
        )}

        {facts.length > 0 && (
          <dl className="mt-[22px] grid grid-cols-3 gap-3 border-t border-border/30 pt-[18px]">
            {facts.map(([label, value]) => (
              <div key={label} className="min-w-0">
                <dt className="font-display text-sm uppercase tracking-[0.14em] text-foreground/45">
                  {label}
                </dt>
                <dd className="mt-0.5 truncate font-display text-[26px] font-bold tabular-nums text-foreground">
                  {value}
                </dd>
              </div>
            ))}
          </dl>
        )}

        <div className="mt-4 flex flex-wrap gap-2">
          <Tag tone={lyricsTone}>{lyricsLabel}</Tag>
          {song.itunesExplicit && <Tag tone="warn">Explicit</Tag>}
          {song.status !== "processed" && <Tag tone="quiet">Processing</Tag>}
        </div>
      </div>
    </motion.aside>
  );
};

export default SongInfoCard;
