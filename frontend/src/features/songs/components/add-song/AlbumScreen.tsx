/**
 * AlbumScreen - one album or single: its cover, then every track.
 */

import React from "react";
import { useYoutubeMusicAlbum } from "@/hooks/api/useYoutubeMusic";
import {
  useAddFlowNavigation,
  type AddFlowStep,
} from "@/hooks/useAddFlowNavigation";
import { formatTime } from "@/utils/formatters";
import {
  BackLink,
  RowsSkeleton,
  ScreenHeader,
  ScreenMessage,
  ScreenTitle,
} from "./ScreenParts";
import { thumbnailAt, loadErrorText } from "./songText";
import { SongList, SongRow } from "./SongRow";

type AlbumStep = Extract<AddFlowStep, { kind: "album" }>;

export const AlbumScreen: React.FC<{ step: AlbumStep }> = ({ step }) => {
  const nav = useAddFlowNavigation();
  const { data, isLoading, error, refetch } = useYoutubeMusicAlbum(
    step.browseId,
  );

  const albumArtists = data?.album.artists.map((a) => a.name).join(", ");
  const back = (
    <BackLink
      label={step.backLabel ?? albumArtists ?? "Back"}
      onClick={() => nav.back(step)}
    />
  );

  if (isLoading || !data) {
    return (
      <div className="flex flex-col gap-4">
        <ScreenHeader back={back}>
          {error ? (
            <ScreenMessage
              title="This album didn't load"
              onRetry={() => refetch()}
            >
              {loadErrorText(error)}
            </ScreenMessage>
          ) : (
            <div className="bg-surface size-32 animate-pulse rounded-xl" />
          )}
        </ScreenHeader>
        {!error && <RowsSkeleton count={8} />}
      </div>
    );
  }

  const { album, tracks } = data;
  const cover = thumbnailAt(album, 256);
  const details = [albumArtists, album.type, album.year]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="flex flex-col gap-3">
      <ScreenHeader back={back}>
        <div className="flex items-end gap-4">
          {cover ? (
            <img
              referrerPolicy="no-referrer"
              src={cover}
              alt=""
              className="bg-surface size-32 shrink-0 rounded-xl object-cover"
            />
          ) : (
            <span className="bg-surface size-32 shrink-0 rounded-xl" />
          )}
          <div className="flex min-w-0 flex-col gap-1.5">
            <ScreenTitle className="text-3xl leading-tight">
              {album.title}
            </ScreenTitle>
            <span className="text-foreground-dim text-sm">{details}</span>
          </div>
        </div>
      </ScreenHeader>

      {tracks.length === 0 ? (
        <ScreenMessage title="No tracks on YouTube Music for this one" />
      ) : (
        <SongList>
          {tracks.map((track, i) => (
            <SongRow
              key={track.videoId ?? `${i}-${track.title}`}
              song={track}
              look="plain"
              subtitle={
                track.durationSeconds
                  ? formatTime(track.durationSeconds)
                  : undefined
              }
            />
          ))}
        </SongList>
      )}
    </div>
  );
};
