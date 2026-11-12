/**
 * ArtistScreen - one artist: their albums in a row that scrolls sideways,
 * oldest first, then their popular songs, then singles, then remix
 * collections. Every release is a tile that opens the album screen.
 *
 * Albums lead because they're how fans who know an artist find a song; the
 * popular songs sit right under them for everyone else.
 */

import React, { useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import {
  useYoutubeMusicArtist,
  useYoutubeMusicArtistSongs,
} from "@/hooks/api/useYoutubeMusic";
import {
  useAddFlowNavigation,
  type AddFlowStep,
} from "@/hooks/useAddFlowNavigation";
import type { YoutubeMusicRelease } from "@/types/Youtube";
import {
  BackLink,
  RowsSkeleton,
  ScreenHeader,
  ScreenMessage,
  ScreenTitle,
  SectionLabel,
} from "./ScreenParts";
import { thumbnailAt, loadErrorText } from "./songText";
import { SongList, SongRow } from "./SongRow";

type ArtistStep = Extract<AddFlowStep, { kind: "artist" }>;

/** "2026 · Single": the year, and the kind of release when it isn't an album. */
const releaseDetails = (release: YoutubeMusicRelease) =>
  [
    release.year,
    release.type && release.type.toLowerCase() !== "album"
      ? release.type.charAt(0).toUpperCase() + release.type.slice(1)
      : null,
  ]
    .filter(Boolean)
    .join(" · ");

/** A release's cover, title and details, as a button that opens it. */
const ReleaseTile: React.FC<{
  release: YoutubeMusicRelease;
  artistName: string;
}> = ({ release, artistName }) => {
  const nav = useAddFlowNavigation();
  const cover = thumbnailAt(release, 400);
  return (
    <button
      type="button"
      disabled={!release.browseId}
      onClick={() =>
        release.browseId &&
        nav.openAlbum(release.browseId, { backLabel: artistName })
      }
      className="focus-visible:ring-ring/50 flex w-full flex-col gap-1.5 rounded-lg text-left outline-none focus-visible:ring-[3px]"
    >
      {cover ? (
        <img
          referrerPolicy="no-referrer"
          src={cover}
          alt=""
          loading="lazy"
          className="bg-surface aspect-square w-full rounded-lg object-cover"
        />
      ) : (
        <span className="bg-surface aspect-square w-full rounded-lg" />
      )}
      <span className="line-clamp-3 leading-tight font-semibold">
        {release.title}
      </span>
      <span className="text-foreground-dim text-sm">
        {releaseDetails(release)}
      </span>
    </button>
  );
};

/** Every album in one row that scrolls sideways, oldest first. With a mouse,
 * arrow buttons page the row so nobody has to shift-scroll. */
const AlbumRow: React.FC<{
  albums: YoutubeMusicRelease[];
  artistName: string;
}> = ({ albums, artistName }) => {
  const viewportRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const [canLeft, setCanLeft] = useState(false);
  const [canRight, setCanRight] = useState(false);

  useEffect(() => {
    const viewport = viewportRef.current;
    const list = listRef.current;
    if (!viewport || !list) return;
    const update = () => {
      setCanLeft(viewport.scrollLeft > 0);
      setCanRight(
        viewport.scrollLeft + viewport.clientWidth < viewport.scrollWidth - 1,
      );
    };
    update();
    viewport.addEventListener("scroll", update, { passive: true });
    // The viewport resizes with the window, the list with its albums
    const observer = new ResizeObserver(update);
    observer.observe(viewport);
    observer.observe(list);
    return () => {
      viewport.removeEventListener("scroll", update);
      observer.disconnect();
    };
  }, [albums]);

  if (albums.length === 0) return null;

  /** Scroll most of a row's width, so the last tile in view stays visible. */
  const page = (direction: -1 | 1) => {
    const viewport = viewportRef.current;
    if (!viewport) return;
    viewport.scrollBy({
      left: direction * viewport.clientWidth * 0.8,
      behavior: "smooth",
    });
  };

  const arrowClass =
    "bg-background/80 hover:bg-background/90 absolute top-18 z-10 hidden -translate-y-1/2 rounded-full desktop:flex";

  return (
    <section className="flex flex-col gap-2.5" aria-labelledby="albums-label">
      <SectionLabel id="albums-label">Albums</SectionLabel>
      <div className="relative">
        <ScrollArea className="w-full" viewportRef={viewportRef}>
          <ul ref={listRef} className="flex w-max gap-3 pb-3">
            {albums.map((album) => (
              <li key={album.browseId ?? album.title} className="w-36 shrink-0">
                <ReleaseTile release={album} artistName={artistName} />
              </li>
            ))}
          </ul>
          <ScrollBar orientation="horizontal" />
        </ScrollArea>
        {canLeft && (
          <Button
            variant="ghost"
            size="icon"
            className={cn(arrowClass, "left-2")}
            onClick={() => page(-1)}
            aria-label="Scroll albums left"
          >
            <ChevronLeft className="size-5" />
          </Button>
        )}
        {canRight && (
          <Button
            variant="ghost"
            size="icon"
            className={cn(arrowClass, "right-2")}
            onClick={() => page(1)}
            aria-label="Scroll albums right"
          >
            <ChevronRight className="size-5" />
          </Button>
        )}
      </div>
    </section>
  );
};

/** Tiles a release grid shows before "See all": two full rows at most widths. */
const GRID_TILES_SHOWN = 8;

interface ReleaseGridProps {
  label: string;
  artistName: string;
  releases: YoutubeMusicRelease[];
}

/** Releases as a grid; past a couple of rows, the rest wait behind "See all". */
const ReleaseGrid: React.FC<ReleaseGridProps> = ({
  label,
  artistName,
  releases,
}) => {
  const [showAll, setShowAll] = useState(false);
  if (releases.length === 0) return null;
  const shown = showAll ? releases : releases.slice(0, GRID_TILES_SHOWN);
  const id = `${label.toLowerCase()}-label`;

  return (
    <section className="flex flex-col gap-2.5" aria-labelledby={id}>
      <SectionLabel id={id}>{label}</SectionLabel>
      <ul className="grid grid-cols-2 gap-x-3 gap-y-4 sm:grid-cols-3 lg:grid-cols-4">
        {shown.map((release) => (
          <li key={release.browseId ?? release.title}>
            <ReleaseTile release={release} artistName={artistName} />
          </li>
        ))}
      </ul>
      {shown.length < releases.length && (
        <Button
          variant="link"
          className="h-11 self-start p-0 text-base font-bold"
          onClick={() => setShowAll(true)}
        >
          See all {releases.length} {label.toLowerCase()}
        </Button>
      )}
    </section>
  );
};

export const ArtistScreen: React.FC<{ step: ArtistStep }> = ({ step }) => {
  const nav = useAddFlowNavigation();
  const [showAllSongs, setShowAllSongs] = useState(false);
  const { data, isLoading, error, refetch } = useYoutubeMusicArtist(
    step.browseId,
  );
  const allSongs = useYoutubeMusicArtistSongs(step.browseId, showAllSongs);

  const back = (
    <BackLink label={step.backLabel ?? "Back"} onClick={() => nav.back(step)} />
  );

  if (isLoading || !data) {
    return (
      // Changed from "min-h-0 flex flex-col gap-4" to let height flow naturally
      <div className="flex flex-col gap-4 pb-6">
        <ScreenHeader back={back}>
          {error ? (
            <ScreenMessage
              title="This artist didn't load"
              onRetry={() => refetch()}
            >
              {loadErrorText(error)}
            </ScreenMessage>
          ) : (
            <div className="bg-surface h-22 w-2/3 animate-pulse rounded-xl" />
          )}
        </ScreenHeader>
        {!error && <RowsSkeleton />}
      </div>
    );
  }

  const { artist } = data;
  const name = artist.name ?? "";
  const avatar = thumbnailAt(artist, 176);
  const songs = (showAllSongs && allSongs.data) || data.topSongs;

  return (
    // Changed from "min-h-0 flex flex-col gap-6" to "flex flex-col gap-6 pb-6"
    <div className="flex flex-col gap-6 pb-6">
      <ScreenHeader back={back}>
        <div className="flex items-center gap-4">
          {avatar ? (
            <img
              referrerPolicy="no-referrer"
              src={avatar}
              alt=""
              className="bg-surface size-22 shrink-0 rounded-full object-cover"
            />
          ) : (
            <span className="bg-surface size-22 shrink-0 rounded-full" />
          )}
          <div className="flex min-w-0 flex-col gap-1">
            <ScreenTitle>{name}</ScreenTitle>
            {artist.subscribers && (
              <span className="text-foreground-dim text-sm">
                {artist.subscribers} subscribers
              </span>
            )}
          </div>
        </div>
      </ScreenHeader>

      <AlbumRow albums={data.albums} artistName={name} />

      {songs.length > 0 && (
        <section className="flex flex-col" aria-labelledby="popular-label">
          <SectionLabel id="popular-label">Popular songs</SectionLabel>
          <SongList className="mt-1.5">
            {songs.map((song) => (
              <SongRow
                key={song.videoId ?? song.title}
                song={song}
                subtitle={song.album}
              />
            ))}
          </SongList>
          {data.hasMoreSongs && !showAllSongs && (
            <Button
              variant="link"
              className="h-11 self-start p-0 text-base font-bold"
              onClick={() => setShowAllSongs(true)}
            >
              Show all popular songs
            </Button>
          )}
          {showAllSongs && allSongs.isLoading && (
            <Loader2 className="text-foreground-dim mt-2 size-5 animate-spin" />
          )}
          {showAllSongs && allSongs.error && (
            <ScreenMessage
              title="The rest didn't load"
              onRetry={() => allSongs.refetch()}
            />
          )}
        </section>
      )}

      <ReleaseGrid label="Singles" artistName={name} releases={data.singles} />
      <ReleaseGrid label="Remixes" artistName={name} releases={data.remixes} />

      {songs.length === 0 &&
        data.albums.length === 0 &&
        data.singles.length === 0 &&
        data.remixes.length === 0 && (
          <ScreenMessage title={`No songs from ${name} on YouTube Music`} />
        )}
    </div>
  );
};
