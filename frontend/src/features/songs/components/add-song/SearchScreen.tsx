/**
 * SearchScreen - "Add a song": the search box, then results sorted by what a
 * guest is looking for.
 *
 * The best match first, then other songs, then the best match's other
 * versions (covers, live takes) folded into one row, then artists. "Can't find
 * it?" swaps in plain YouTube results for anything YouTube Music doesn't have.
 */

import React, { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { useYoutubeMusicSearch } from "@/hooks/api/useYoutubeMusic";
import { useYoutubeVideoSearch } from "@/hooks/useYoutubeVideoSearch";
import {
  useAddFlowNavigation,
  type AddFlowStep,
} from "@/hooks/useAddFlowNavigation";
import { cn } from "@/lib/utils";
import { formatTime } from "@/utils/formatters";
import type {
  YoutubeMusicArtistSearchResult,
  YoutubeMusicSong,
  YoutubeVideoSearchResult,
} from "@/types/Youtube";
import { SongProcessingTracker } from "../../processing/SongProcessingTracker";
import { useSongRowState } from "./addSongContext";
import { SearchField } from "./SearchField";
import {
  BackLink,
  RowsSkeleton,
  ScreenHeader,
  ScreenMessage,
  ScreenTitle,
  SectionLabel,
} from "./ScreenParts";
import { artistNames, thumbnailAt, loadErrorText } from "./songText";
import { PreviewArt, SongAddButton, SongList, SongRow } from "./SongRow";

type SearchStep = Extract<AddFlowStep, { kind: "search" }>;

/** Names compared the way a guest would: case and accents ignored. */
const nameKey = (name: string) =>
  name
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .trim()
    .toLowerCase();

const songDetails = (song: YoutubeMusicSong, withArtist: boolean) =>
  [
    withArtist ? artistNames(song) : song.album,
    song.durationSeconds ? formatTime(song.durationSeconds) : null,
  ]
    .filter(Boolean)
    .join(" · ");

/** The artists of a song, each a link to their artist screen when it has one. */
const ArtistLinks: React.FC<{ song: YoutubeMusicSong; backLabel: string }> = ({
  song,
  backLabel,
}) => {
  const nav = useAddFlowNavigation();
  return (
    <span className="flex flex-wrap gap-x-1 text-base font-bold">
      {song.artists.map((artist, i) => (
        <span key={`${artist.name}-${i}`}>
          {artist.id ? (
            <Button
              variant="link"
              className="h-auto p-0 text-base font-bold"
              onClick={() => nav.openArtist(artist.id!, { backLabel })}
            >
              {artist.name}
            </Button>
          ) : (
            artist.name
          )}
          {i < song.artists.length - 1 && ","}
        </span>
      ))}
    </span>
  );
};

const BestMatchCard: React.FC<{
  song: YoutubeMusicSong;
  backLabel: string;
}> = ({ song, backLabel }) => {
  const state = useSongRowState(song);
  return (
    <Card variant="surface" className="gap-3.5 p-3.5">
      <div className="flex items-center gap-3.5">
        <PreviewArt song={song} className="size-23" />
        <div className="flex min-w-0 flex-col gap-1">
          <span className="font-display text-2xl leading-tight break-words">
            {song.title}
          </span>
          <ArtistLinks song={song} backLabel={backLabel} />
          <span className="text-foreground-dim text-sm">
            {songDetails(song, false)}
          </span>
        </div>
      </div>
      <SongAddButton
        song={song}
        state={state}
        source="youtube_music"
        size="wide"
      />
      {state.kind === "processing" && (
        <SongProcessingTracker songId={state.songId} />
      )}
    </Card>
  );
};

const OtherVersions: React.FC<{ songs: YoutubeMusicSong[] }> = ({ songs }) => {
  const [open, setOpen] = useState(false);
  const count = songs.length;
  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger asChild>
        <button
          type="button"
          className="border-border/60 hover:bg-surface-hover focus-visible:ring-ring/50 flex min-h-16 w-full items-center gap-3 rounded-xl border-2 border-dashed px-3.5 py-3 text-left outline-none focus-visible:ring-[3px]"
        >
          <span className="flex flex-1 flex-col gap-0.5">
            <span className="font-semibold">
              {count === 1
                ? "1 other version of this song"
                : `${count} other versions of this song`}
            </span>
            <span className="text-foreground-dim text-sm">
              Covers, live takes, remixes and remakes
            </span>
          </span>
          <ChevronDown
            className={cn(
              "text-primary size-5 shrink-0 transition-transform",
              open && "rotate-180",
            )}
          />
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <SongList className="mt-2">
          {songs.map((song) => (
            <SongRow
              key={song.videoId}
              song={song}
              subtitle={songDetails(song, true)}
            />
          ))}
        </SongList>
      </CollapsibleContent>
    </Collapsible>
  );
};

const ArtistChips: React.FC<{
  artists: YoutubeMusicArtistSearchResult[];
  backLabel: string;
}> = ({ artists, backLabel }) => {
  const nav = useAddFlowNavigation();
  return (
    <section className="flex flex-col gap-2.5" aria-labelledby="artists-label">
      <SectionLabel id="artists-label">Artists</SectionLabel>
      <div className="flex flex-wrap gap-2.5">
        {artists.map((artist) => {
          const avatar = thumbnailAt(artist, 72);
          return (
            <Button
              key={artist.browseId}
              variant="pill"
              size="touch"
              className="bg-surface text-surface-foreground hover:bg-surface-hover gap-2.5 rounded-full py-1.5 pr-4 pl-1.5"
              onClick={() => nav.openArtist(artist.browseId, { backLabel })}
            >
              {avatar ? (
                <img
                  src={avatar}
                  alt=""
                  referrerPolicy="no-referrer"
                  className="size-9 rounded-full"
                />
              ) : (
                <span className="bg-surface-raised size-9 rounded-full" />
              )}
              {artist.name}
            </Button>
          );
        })}
      </div>
    </section>
  );
};

/** A plain YouTube video as a song row's song; the channel stands in for the artist. */
const videoAsSong = (video: YoutubeVideoSearchResult): YoutubeMusicSong => ({
  videoId: video.id,
  title: video.title,
  artists: video.channel ? [{ name: video.channel }] : [],
  artist: video.channel,
  album: null,
  albumId: null,
  durationSeconds: video.duration || null,
  isExplicit: false,
  thumbnails: video.thumbnail ? [{ url: video.thumbnail }] : [],
  library: video.library,
});

const YouTubeResults: React.FC<{ query: string; onBack: () => void }> = ({
  query,
  onBack,
}) => {
  const { data, isLoading, error, refetch } = useYoutubeVideoSearch({
    query,
  });

  return (
    <section className="flex flex-col gap-2" aria-labelledby="youtube-label">
      <SectionLabel id="youtube-label">YouTube</SectionLabel>
      <Button
        variant="link"
        className="h-11 self-start p-0 text-base font-bold"
        onClick={onBack}
      >
        Back to YouTube Music results
      </Button>
      {isLoading ? (
        <RowsSkeleton />
      ) : error ? (
        <ScreenMessage
          title="YouTube search didn't load"
          onRetry={() => refetch()}
        >
          {loadErrorText(error)}
        </ScreenMessage>
      ) : data.length === 0 ? (
        <ScreenMessage title={`Nothing on YouTube for “${query}”`} />
      ) : (
        <SongList>
          {data.map((video) => {
            const song = videoAsSong(video);
            return (
              <SongRow
                key={video.id}
                song={song}
                source="youtube"
                subtitle={songDetails(song, true)}
              />
            );
          })}
        </SongList>
      )}
    </section>
  );
};

const MusicResults: React.FC<{
  query: string;
  findArtist?: boolean;
  openTopArtist?: boolean;
  onSearchYouTube: () => void;
}> = ({ query, findArtist, openTopArtist, onSearchYouTube }) => {
  const nav = useAddFlowNavigation();
  const { data, isLoading, error, refetch } = useYoutubeMusicSearch(query);
  const backLabel = `Results for “${query}”`;

  const triedFindArtist = useRef(false);
  useEffect(() => {
    if (!data || triedFindArtist.current) return;
    if (findArtist) {
      // From the library's "Browse artist": open the artist only when one's
      // name is exactly the query, so a near miss never lands on someone else.
      triedFindArtist.current = true;
      const match = data.artists.find(
        (a) => nameKey(a.name) === nameKey(query),
      );
      // In the search's place, so back returns to the songbook it came from.
      if (match) {
        nav.openArtist(match.browseId, {
          replace: true,
          backLabel: "Songbook",
        });
      }
    } else if (openTopArtist) {
      // A picked suggestion: open the artist only when YouTube Music's own top
      // result is one. A name match isn't enough; "creep" and "yesterday" are
      // artists too. These results stay behind it, without the flag, so back
      // shows them instead of bouncing to the artist again.
      triedFindArtist.current = true;
      if (data.topArtistId) {
        nav.search(query);
        nav.openArtist(data.topArtistId, { backLabel });
      }
    }
  }, [findArtist, openTopArtist, data, query, nav, backLabel]);

  if (isLoading) return <RowsSkeleton />;
  if (error) {
    return (
      <ScreenMessage title="Search didn't load" onRetry={() => refetch()}>
        {loadErrorText(error)}
      </ScreenMessage>
    );
  }
  if (!data) return null;

  const { bestMatch, otherSongs, otherVersions, artists } = data;

  return (
    <div className="flex flex-col gap-7">
      {!bestMatch && artists.length === 0 && (
        <ScreenMessage title={`No songs found for “${query}”`}>
          Check the spelling, or search YouTube below.
        </ScreenMessage>
      )}

      {bestMatch && (
        <section
          className="flex flex-col gap-2.5"
          aria-labelledby="best-match-label"
        >
          <SectionLabel id="best-match-label">Best match</SectionLabel>
          <BestMatchCard song={bestMatch} backLabel={backLabel} />
        </section>
      )}

      {otherSongs.length > 0 && (
        <section className="flex flex-col" aria-labelledby="other-songs-label">
          <SectionLabel id="other-songs-label">Other songs</SectionLabel>
          <SongList className="mt-1.5">
            {otherSongs.map((song) => (
              <SongRow
                key={song.videoId}
                song={song}
                subtitle={songDetails(song, true)}
              />
            ))}
          </SongList>
        </section>
      )}

      {otherVersions.length > 0 && <OtherVersions songs={otherVersions} />}

      {artists.length > 0 && (
        <ArtistChips artists={artists} backLabel={backLabel} />
      )}

      <section className="border-border/40 flex flex-col gap-1.5 border-t pt-3">
        <p className="font-semibold">Can't find it?</p>
        <p className="text-foreground-dim text-sm">
          Search all of YouTube instead. Sound and song details may be rougher.
        </p>
        <Button
          variant="link"
          className="h-11 self-start p-0 text-base font-bold whitespace-normal"
          onClick={onSearchYouTube}
        >
          Search YouTube for “{query}”
        </Button>
      </section>
    </div>
  );
};

interface SearchScreenProps {
  step: SearchStep;
  /** The way out of the add flow: the songbook. */
  onExit: () => void;
}

export const SearchScreen: React.FC<SearchScreenProps> = ({ step, onExit }) => {
  const nav = useAddFlowNavigation();
  const query = step.query?.trim() ?? "";
  const [youtubeQuery, setYoutubeQuery] = useState<string | null>(null);
  // Plain YouTube results belong to the search that asked for them.
  const showYouTube = youtubeQuery !== null && youtubeQuery === query;

  return (
    <div className="flex flex-col gap-4">
      <ScreenHeader back={<BackLink label="Songbook" onClick={onExit} />}>
        <ScreenTitle>Add a song</ScreenTitle>
      </ScreenHeader>

      <SearchField
        query={query}
        onSearch={(next, how) =>
          nav.search(next, { openTopArtist: how === "picked" })
        }
        autoFocus={!query}
      />

      <div className="pt-2">
        {!query ? (
          <p className="text-foreground-dim">
            Search for a song or an artist. Pick a suggestion or press Search to
            see songs.
          </p>
        ) : showYouTube ? (
          <YouTubeResults query={query} onBack={() => setYoutubeQuery(null)} />
        ) : (
          <MusicResults
            query={query}
            findArtist={step.findArtist}
            openTopArtist={step.openTopArtist}
            onSearchYouTube={() => setYoutubeQuery(query)}
          />
        )}
      </div>
    </div>
  );
};
