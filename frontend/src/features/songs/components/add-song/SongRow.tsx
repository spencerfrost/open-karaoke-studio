/**
 * SongRow - one song in any of the add flow's lists (other songs, other
 * versions, popular songs, album tracks, plain YouTube results).
 *
 * The art doubles as the preview button. The button on the right reads the
 * song's library copy and this page's own submissions; once the song is on its
 * way, its progress shows under the row. A song already in the songbook can
 * be queued from here instead.
 */

import React, { useState } from "react";
import { toast } from "sonner";
import { Check, Loader2, Pause, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useSongs } from "@/hooks/api/useSongs";
import { createLogger } from "@/lib/logger";
import { cn } from "@/lib/utils";
import type { Song } from "@/types/Song";
import type { YoutubeMusicSong } from "@/types/Youtube";
import { SongProcessingTracker } from "../../processing/SongProcessingTracker";
import { QueueSingerDialog } from "../song-card/QueueSingerDialog";
import { useQueueSong } from "../../hooks/useQueueSong";
import {
  useAddSong,
  useSongRowState,
  type SongRowState,
} from "./addSongContext";
import { usePreview } from "./previewContext";
import { artistNames, thumbnailAt } from "./songText";
import type { SongInput } from "../../hooks/useSongCreation";

const logger = createLogger("component:SongRow");

interface PreviewArtProps {
  song: YoutubeMusicSong;
  /** "art": the song's cover; "plain": a round button, for album tracks. */
  look?: "art" | "plain";
  className?: string;
}

/** The song's art as a button that starts and pauses its preview. */
export const PreviewArt: React.FC<PreviewArtProps> = ({
  song,
  look = "art",
  className,
}) => {
  const track = song.videoId
    ? {
        videoId: song.videoId,
        title: song.title ?? "",
        artist: artistNames(song),
      }
    : null;
  const { status, toggle } = usePreview(track);
  const art = look === "art" ? thumbnailAt(song, 192) : undefined;

  const icon =
    status === "loading" ? (
      <Loader2 className="size-5 animate-spin" />
    ) : status === "playing" ? (
      <Pause className="size-5" />
    ) : (
      <Play className="ml-0.5 size-5" />
    );

  if (!track) {
    return art ? (
      <img
        referrerPolicy="no-referrer"
        src={art}
        alt=""
        className={cn("shrink-0 rounded-lg object-cover", className)}
      />
    ) : (
      <div className={cn("shrink-0", className)} />
    );
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={`${status === "playing" ? "Pause" : "Preview"} ${song.title}`}
      className={cn(
        "relative flex shrink-0 items-center justify-center overflow-hidden outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50",
        look === "art"
          ? "rounded-lg bg-surface-raised"
          : "rounded-full bg-surface text-surface-foreground",
        className,
      )}
    >
      {art && (
        <img
          referrerPolicy="no-referrer"
          src={art}
          alt=""
          loading="lazy"
          className="absolute inset-0 size-full object-cover"
        />
      )}
      <span
        className={cn(
          "relative flex items-center justify-center",
          art && "size-10 rounded-full bg-overlay/70 text-primary",
        )}
      >
        {icon}
      </span>
    </button>
  );
};

/**
 * "Sing it" on a song already in the songbook: queues the library copy the
 * way the songbook's own queue button does (the confirm screen on the stage,
 * "who's singing?" on a host's device, straight in for a guest).
 */
const SingItButton: React.FC<{ songId: string; wide: boolean }> = ({
  songId,
  wide,
}) => {
  const { fetchSong } = useSongs();
  const { queueSong, addToQueue } = useQueueSong();
  const [loading, setLoading] = useState(false);
  const [pickingFor, setPickingFor] = useState<Song | null>(null);

  const singIt = async () => {
    setLoading(true);
    try {
      const song = await fetchSong(songId);
      if (!queueSong(song, () => setPickingFor(song))) {
        toast.error("Start a session on the Stage to queue songs.");
      }
    } catch (error) {
      logger.error("Couldn't load the songbook's copy:", error);
      toast.error("That song didn't load. Try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Button
        variant="outline-foreground"
        size={wide ? "xl" : "touch"}
        className={cn(wide && "w-full")}
        disabled={loading}
        onClick={singIt}
      >
        {loading && <Loader2 className="animate-spin" />}
        Sing it
      </Button>
      {pickingFor && (
        <QueueSingerDialog
          song={pickingFor}
          isOpen
          onClose={() => setPickingFor(null)}
          onQueue={(name) => addToQueue(pickingFor, name)}
        />
      )}
    </>
  );
};

interface SongAddButtonProps {
  song: YoutubeMusicSong;
  state: SongRowState;
  source: SongInput["source"];
  /** "row": compact, on the right of a row; "wide": the best match's full-width button. */
  size?: "row" | "wide";
}

export const SongAddButton: React.FC<SongAddButtonProps> = ({
  song,
  state,
  source,
  size = "row",
}) => {
  const { addSong } = useAddSong();
  const wide = size === "wide";
  const statusClass = cn(
    "flex items-center gap-1 text-sm leading-tight font-semibold",
    wide ? "h-14 justify-center text-base" : "w-24 justify-end text-right",
  );

  switch (state.kind) {
    case "add":
    case "retry":
      return (
        <Button
          variant={state.kind === "add" ? "primary" : "outline-foreground"}
          size={wide ? "xl" : "touch"}
          className={cn(wide && "w-full")}
          onClick={() => addSong(song, source)}
        >
          {state.kind === "retry"
            ? "Try again"
            : wide
              ? "Add to songbook"
              : "Add"}
        </Button>
      );
    case "adding":
      return (
        <Button
          variant="outline"
          size={wide ? "xl" : "touch"}
          className={cn(wide && "w-full")}
          disabled
        >
          <Loader2 className="animate-spin" />
          Adding
        </Button>
      );
    case "ready":
      return (
        <div
          className={cn(
            "flex shrink-0 flex-col gap-1",
            wide ? "items-stretch" : "items-end",
          )}
        >
          <span
            className={cn(
              "text-foreground-dim flex items-center gap-1 text-xs font-semibold",
              wide && "justify-center text-sm",
            )}
          >
            <Check className="text-section-label size-3.5 shrink-0" />
            In the songbook
          </span>
          <SingItButton songId={state.songId} wide={wide} />
        </div>
      );
    case "processing":
      return (
        <span className={cn(statusClass, "text-section-label")}>
          Getting it ready…
        </span>
      );
    case "unavailable":
      return (
        <span className={cn(statusClass, "text-foreground-dim")}>
          Not available
        </span>
      );
  }
};

interface SongRowProps {
  song: YoutubeMusicSong;
  /** The second line: artist and length, the album, or just the length. */
  subtitle?: React.ReactNode;
  look?: PreviewArtProps["look"];
  source?: SongInput["source"];
}

export const SongRow: React.FC<SongRowProps> = ({
  song,
  subtitle,
  look = "art",
  source = "youtube_music",
}) => {
  const state = useSongRowState(song);

  return (
    <li className="border-border/40 border-b py-2 last:border-b-0">
      <div className="flex items-center gap-3">
        <PreviewArt
          song={song}
          look={look}
          className={look === "art" ? "size-14" : "size-11"}
        />
        <div className="flex min-w-0 flex-1 flex-col gap-0.5">
          <span className="truncate font-semibold" title={song.title ?? ""}>
            {song.title}
          </span>
          {subtitle && (
            <span className="text-foreground-dim truncate text-sm">
              {subtitle}
            </span>
          )}
        </div>
        <SongAddButton song={song} state={state} source={source} />
      </div>
      {state.kind === "processing" && (
        <SongProcessingTracker songId={state.songId} className="mt-2" />
      )}
    </li>
  );
};

/** A list of SongRows, with the plain markup every list shares. */
export const SongList: React.FC<{
  children: React.ReactNode;
  className?: string;
}> = ({ children, className }) => (
  <ul className={cn("flex flex-col", className)}>{children}</ul>
);
