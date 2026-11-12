// frontend/src/hooks/api/useYoutubeMusic.ts
import { keepPreviousData } from "@tanstack/react-query";
import { useApiQuery } from "./useApi";
import {
  YoutubeMusicSearchResponse,
  YoutubeMusicArtistResponse,
  YoutubeMusicAlbumResponse,
  YoutubeMusicSong,
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

/** Suggestions for a partly typed search. Keeps the last list while the next loads. */
export function useYoutubeMusicSuggestions(text: string, enabled = true) {
  return useApiQuery<string[], ["youtube-music-suggestions", string]>(
    ["youtube-music-suggestions", text],
    `youtube-music/suggestions?q=${encodeURIComponent(text)}`,
    {
      enabled: enabled && !!text,
      staleTime: 1000 * 60 * 5,
      placeholderData: keepPreviousData,
      retry: false,
    },
  );
}

export function useYoutubeMusicArtist(artistId: string | null) {
  return useApiQuery<
    YoutubeMusicArtistResponse,
    ["youtube-music-artist", string]
  >(["youtube-music-artist", artistId!], `youtube-music/artist/${artistId}`, {
    enabled: !!artistId,
    staleTime: 1000 * 60 * 15, // 15 minutes - artist data doesn't change often
    retry: 1,
  });
}

/** Every one of the artist's popular songs, for "Show all popular songs". */
export function useYoutubeMusicArtistSongs(
  artistId: string | null,
  enabled: boolean,
) {
  return useApiQuery<
    YoutubeMusicSong[],
    ["youtube-music-artist-songs", string]
  >(
    ["youtube-music-artist-songs", artistId!],
    `youtube-music/artist/${artistId}/songs`,
    {
      enabled: enabled && !!artistId,
      staleTime: 1000 * 60 * 15,
      retry: 1,
    },
  );
}

export function useYoutubeMusicAlbum(albumId: string | null) {
  return useApiQuery<
    YoutubeMusicAlbumResponse,
    ["youtube-music-album", string]
  >(
    ["youtube-music-album", albumId!],
    `youtube-music/album/${albumId}/tracks`,
    {
      enabled: !!albumId,
      staleTime: 1000 * 60 * 15, // 15 minutes
      retry: 1,
    },
  );
}
