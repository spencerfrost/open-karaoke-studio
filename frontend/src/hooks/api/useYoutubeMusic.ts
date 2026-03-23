// frontend/src/hooks/useYoutubeMusic.ts
import { useApiQuery } from "./useApi";
import {
  YoutubeMusicSearchResponse,
  YoutubeMusicArtistResponse,
  YoutubeMusicAlbumTracksResponse,
  YoutubeMusicAlbum,
} from "../../types/Youtube";

export function useYoutubeMusicSearch(query: string, enabled: boolean = true) {
  return useApiQuery<
    YoutubeMusicSearchResponse,
    ["youtube-music-search", string]
  >(
    ["youtube-music-search", query],
    `youtube-music/search?q=${encodeURIComponent(query)}`,
    {
      enabled: enabled && !!query,
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  );
}

export function useYoutubeMusicArtist(
  artistId: string | null,
  limit: number = 12,
  enabled: boolean = true,
) {
  return useApiQuery<
    { data: YoutubeMusicArtistResponse; error: string | null },
    ["youtube-music-artist", string, number]
  >(
    ["youtube-music-artist", artistId!, limit],
    `youtube-music/artist/${artistId}?limit=${limit}`,
    {
      enabled: enabled && !!artistId,
      staleTime: 1000 * 60 * 15, // 15 minutes - artist data doesn't change often
      retry: 1,
    },
  );
}

export function useYoutubeMusicArtistReleases(
  artistId: string | null,
  channelId: string | null,
  params: string | null,
  enabled: boolean = false,
) {
  return useApiQuery<
    { data: YoutubeMusicAlbum[]; error: string | null },
    ["youtube-music-releases", string, string, string]
  >(
    ["youtube-music-releases", artistId!, channelId!, params!],
    `youtube-music/artist/${artistId}/releases?channel_id=${encodeURIComponent(channelId ?? "")}&params=${encodeURIComponent(params ?? "")}`,
    {
      enabled: enabled && !!artistId && !!channelId && !!params,
      staleTime: 1000 * 60 * 15,
      retry: 1,
    },
  );
}

export function useYoutubeMusicAlbumTracks(
  albumId: string | null,
  enabled: boolean = true,
) {
  return useApiQuery<
    { data: YoutubeMusicAlbumTracksResponse; error: string | null },
    ["youtube-music-album", string]
  >(
    ["youtube-music-album", albumId!],
    `youtube-music/album/${albumId}/tracks`,
    {
      enabled: enabled && !!albumId,
      staleTime: 1000 * 60 * 15, // 15 minutes
      retry: 1,
    },
  );
}
