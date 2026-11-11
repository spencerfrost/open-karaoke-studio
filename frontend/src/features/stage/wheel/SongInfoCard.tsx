/**
 * SongInfoCard - what the song under the cursor is, on the right of the wheel.
 *
 * Shown only while the song column is at the front: the one time the right of
 * the screen is empty. Clicking it picks the song. It sits on the wheel's flat frame, beside the cylinder
 * rather than on it, so the ring's 3D transforms never touch it.
 *
 * Built around what the library actually has: the video still leads because
 * most songs have one, and any fact a song lacks is left out rather than shown
 * as "—", so a sparse song gets a shorter card, not a card of blanks.
 *
 * Most videos are album track uploads, whose still *is* the album cover. Those
 * show the cover once, sharp and square over a blurred copy of itself; only a
 * video with a picture of its own gets the still with the cover inset.
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
  songCoverSources,
  songHeroSources,
  stillIsCover,
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
  /**
   * A click on the card: picks the song under the cursor, the same as a click
   * on its title. Guests click the card far more than the title, which
   * doesn't look clickable once it is already the highlighted one.
   */
  onPick: () => void;
}

const LYRICS_TAG: Record<LyricsKind, [string, TagTone]> = {
  "word-synced": ["Word-synced", "normal"],
  synced: ["Synced", "normal"],
  plain: ["Plain lyrics", "quiet"],
  none: ["No lyrics", "quiet"],
};

type TagTone = "normal" | "warn" | "quiet";

/** How far the card dims while the cursor is off the song it shows. */
const STALE_OPACITY = 0.35;

const Tag: React.FC<{ tone: TagTone; children: React.ReactNode }> = ({
  tone,
  children,
}) => (
  <span
    className={cn(
      "rounded-full px-3 py-1 font-display text-base font-bold uppercase tracking-[0.08em]",
      tone === "normal" && "bg-primary/15 text-primary",
      tone === "warn" && "bg-accent/20 text-accent",
      tone === "quiet" && "bg-foreground/10 text-foreground-dim",
    )}
  >
    {children}
  </span>
);

const SongInfoCard: React.FC<SongInfoCardProps> = ({
  song,
  pending,
  centerY,
  onPick,
}) => {
  const reducedMotion = useReducedMotion() ?? false;
  const slide = reducedMotion ? 0 : 24;
  const ms = reducedMotion ? 0 : 220;

  const hasStill = !!(song.thumbnail || song.videoId);
  const coverOnly = hasStill && stillIsCover(song);
  // Without a still the cover is the hero; an inset would repeat it.
  const showCover = hasStill && !coverOnly && !!song.albumCoverUrl;

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
      onClick={onPick}
      className="absolute right-14 w-[400px] cursor-pointer rounded-[20px] bg-surface/95 p-6 shadow-[0_20px_60px_rgba(0,0,0,.5)] ring-1 ring-border/30 transition-shadow hover:ring-2 hover:ring-primary/60"
      style={{ top: centerY, y: "-50%" }}
      initial={{ opacity: 0, x: slide }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: slide }}
      // The ring's turn easing, so the card arrives with the column.
      transition={{ duration: ms / 1000, ease: [0.2, 0.8, 0.25, 1] }}
    >
      {/* The artwork dims itself: it lags the text by a load, and a wrapper
          dimming both would brighten the old image before the new arrived. */}
      <div className={cn("relative", showCover ? "mb-16" : "mb-5")}>
        {coverOnly ? (
          <div className="relative aspect-video w-full overflow-hidden rounded-xl shadow-[0_8px_30px_rgba(0,0,0,.45)]">
            <WheelArtwork
              sources={songCoverSources(song)}
              pending={pending}
              staleOpacity={STALE_OPACITY}
              className="absolute -inset-[10%] z-0 rounded-none"
              layerClassName="blur-2xl brightness-[.55] saturate-[1.2]"
            />
            {/* A set size, not a stretched height and aspect ratio: its
                layers are all absolute, so a shrink-to-fit width would be 0.
                352px card content → 198px tall still, less 12px each side. */}
            <WheelArtwork
              sources={songCoverSources(song)}
              fallback={tileInitial(song.album || song.title)}
              pending={pending}
              staleOpacity={STALE_OPACITY}
              className="absolute left-1/2 top-1/2 z-[1] size-[174px] -translate-x-1/2 -translate-y-1/2 shadow-[0_10px_30px_rgba(0,0,0,.5)]"
            />
          </div>
        ) : (
          <WheelArtwork
            sources={songHeroSources(song)}
            fallback={tileInitial(song.title)}
            pending={pending}
            staleOpacity={STALE_OPACITY}
            className="aspect-video w-full shadow-[0_8px_30px_rgba(0,0,0,.45)]"
          />
        )}
        {showCover && (
          <WheelArtwork
            sources={[song.albumCoverUrl]}
            fallback={tileInitial(song.album || song.title)}
            pending={pending}
            staleOpacity={STALE_OPACITY}
            className="absolute -bottom-12 left-[18px] size-[116px] shadow-[0_10px_30px_rgba(0,0,0,.5)] ring-4 ring-surface"
          />
        )}
      </div>

      <div
        style={{
          opacity: pending ? STALE_OPACITY : 1,
          transition: `opacity ${reducedMotion ? 0 : 120}ms`,
        }}
      >
        <h3 className="line-clamp-2 text-balance font-display text-[40px] font-extrabold leading-[1.05] text-foreground">
          {song.title}
        </h3>
        <div className="mt-1 truncate text-2xl text-foreground">
          {songByline(song)}
        </div>
        {song.album && (
          <div className="mt-0.5 truncate text-xl text-foreground-dim">
            {song.album}
          </div>
        )}

        {facts.length > 0 && (
          <dl className="mt-[22px] grid grid-cols-3 gap-3 border-t border-border/30 pt-[18px]">
            {facts.map(([label, value]) => (
              <div key={label} className="min-w-0">
                <dt className="font-display text-sm uppercase tracking-[0.14em] text-foreground-faint">
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
          {song.explicit && <Tag tone="warn">Explicit</Tag>}
          {song.status !== "processed" && <Tag tone="quiet">Processing</Tag>}
        </div>
      </div>
    </motion.aside>
  );
};

export default SongInfoCard;
