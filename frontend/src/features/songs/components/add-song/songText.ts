/** Small text and art helpers the add-song screens share. */

import type { YoutubeMusicSong } from "@/types/Youtube";

// YouTube Music's image URLs end in a size: "=w226-h226-l90-rj".
const SIZE_SUFFIX = /=w\d+-h\d+[^/]*$/;

/**
 * An item's art as a square image `px` wide (drawn size, times two for sharp
 * screens). YouTube Music resizes and crops to any size its URL asks for, so
 * an artist's 2432×1013 banner comes back as a square avatar. Other images
 * (a plain YouTube video's) come back as they are.
 */
export const thumbnailAt = (
  item: { thumbnails: { url: string }[] },
  px: number,
): string | undefined => {
  const url = item.thumbnails[item.thumbnails.length - 1]?.url;
  return url && SIZE_SUFFIX.test(url)
    ? url.replace(SIZE_SUFFIX, `=w${px}-h${px}-p-l90-rj`)
    : url;
};

export const artistNames = (song: YoutubeMusicSong) =>
  song.artists.map((a) => a.name).join(", ");

/** "That didn't load" in a guest's words; the server's 502 detail says the same. */
export const loadErrorText = (error: Error | null) =>
  error?.message && !error.message.startsWith("HTTP error!")
    ? error.message
    : "Check the connection and try again.";
