import React from "react";
import { ExternalLink, Music } from "lucide-react";
import { useSongs } from "@/hooks/api/useSongs";
import { cn } from "@/lib/utils";
import { formatTime } from "@/utils/formatters";
import type { Song } from "@/types/Song";
import { KaraokePreview } from "./KaraokePreview";
import { StemPreview } from "./StemPreview";

/** "Oct 2, 2026"; null for a missing or unreadable date. */
function formatDay(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const when = new Date(iso);
  if (Number.isNaN(when.getTime())) return null;
  return when.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function sourceLink(song: Song): string | null {
  if (song.sourceUrl) return song.sourceUrl;
  if (song.videoId) return `https://www.youtube.com/watch?v=${song.videoId}`;
  return null;
}

/** What the list knows about the song, shown until the full record loads. */
export interface SongBasics {
  id: string;
  title: string;
  artist: string;
}

/**
 * Who, what and where from: artwork, title, artist, album, source and when
 * it was added. Loads the full song record itself.
 */
export const SongSummary: React.FC<{
  basics: SongBasics;
  size?: "md" | "sm";
}> = ({ basics, size = "md" }) => {
  const { useSong, getArtworkUrl } = useSongs();
  // Ghost records and the like may 404; the basics still show.
  const { data: song } = useSong(basics.id, { retry: false });
  const artwork = song ? getArtworkUrl(song, "medium") : null;
  const link = song ? sourceLink(song) : null;
  const added = formatDay(song?.dateAdded);

  const facts = [
    song?.album && [song.album, song.year].filter(Boolean).join(", "),
    song?.duration ? formatTime(song.duration) : null,
    added && `Added ${added}`,
  ].filter(Boolean);

  return (
    <div className="flex min-w-0 gap-4">
      <div
        className={cn(
          "flex shrink-0 items-center justify-center overflow-hidden rounded-md bg-muted",
          size === "md" ? "h-24 w-24" : "h-16 w-16",
        )}
      >
        {artwork ? (
          <img src={artwork} alt="" className="h-full w-full object-cover" />
        ) : (
          <Music className="h-6 w-6 text-muted-foreground" />
        )}
      </div>
      <div className="min-w-0 space-y-0.5">
        <p
          className={cn(
            "font-semibold leading-tight",
            size === "md" ? "text-xl" : "text-base",
          )}
        >
          {song?.title ?? basics.title}
        </p>
        <p className="text-muted-foreground">{song?.artist ?? basics.artist}</p>
        {facts.length > 0 && (
          <p className="text-sm text-muted-foreground">{facts.join(" · ")}</p>
        )}
        {song?.source && (
          <p className="text-sm text-muted-foreground">
            From{" "}
            {link ? (
              <a
                href={link}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 underline underline-offset-2 hover:text-foreground"
              >
                {song.source}
                <ExternalLink className="h-3 w-3" />
              </a>
            ) : (
              song.source
            )}
          </p>
        )}
      </div>
    </div>
  );
};

/**
 * The right side of a review list: the song, a listen, then what this list
 * knows about it (`details`) and what can be done (`children`). Given
 * `lyrics`, the listen plays them along like the stage does.
 */
export const SongPanel: React.FC<{
  basics: SongBasics;
  /** False when the song has no audio files to play. */
  hasAudio?: boolean;
  lyrics?: { syncedLyrics?: string; plainLyrics?: string };
  details?: React.ReactNode;
  children?: React.ReactNode;
}> = ({ basics, hasAudio = true, lyrics, details, children }) => (
  <div className="space-y-5">
    <SongSummary basics={basics} />
    {hasAudio &&
      (lyrics ? (
        <KaraokePreview songId={basics.id} {...lyrics} />
      ) : (
        <StemPreview songId={basics.id} />
      ))}
    {details}
    {children && (
      <div className="space-y-4 border-t border-border/60 pt-4">{children}</div>
    )}
  </div>
);
