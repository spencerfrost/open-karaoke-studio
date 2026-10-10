import type { JobKind } from "./hooks/useBatchJobs";

/* What each batch job is called and counts, for the jobs page and overview. */

export interface JobInfo {
  name: string;
  description: string;
  /** What the job counts: songs, or artists. */
  unit: [singular: string, plural: string];
}

export const JOB_INFO: Record<JobKind, JobInfo> = {
  loudness: {
    name: "Loudness",
    description:
      "Measures how loud each song plays, so the volume evens out between songs. A second or two per song.",
    unit: ["song", "songs"],
  },
  vocal_range: {
    name: "Vocal range",
    description:
      "Finds the lowest and highest sung note from the vocals track. 10–30 seconds per song.",
    unit: ["song", "songs"],
  },
  duration: {
    name: "Song length",
    description: "Reads each song's length from its audio file.",
    unit: ["song", "songs"],
  },
  album_covers: {
    name: "Album covers",
    description:
      "Downloads the cover for albums that don't have one yet, from iTunes.",
    unit: ["album", "albums"],
  },
  song_albums: {
    name: "Albums for songs",
    description:
      "Finds the album (and its cover) on iTunes for songs that aren't on one.",
    unit: ["song", "songs"],
  },
  fingerprint: {
    name: "AcoustID fingerprints",
    description:
      "Identifies each song from its audio, so its title and artist can be checked.",
    unit: ["song", "songs"],
  },
  artist_images: {
    name: "Artist photos",
    description: "Fetches a photo of each artist from Discogs.",
    unit: ["artist", "artists"],
  },
  lyrics_alignment: {
    name: "Lyrics alignment",
    description:
      "Times lyrics word by word to the singing. Each song is queued as its own job, and the coverage fills in as they finish.",
    unit: ["song", "songs"],
  },
};

export function countOf(
  n: number,
  [singular, plural]: JobInfo["unit"],
): string {
  return `${n.toLocaleString()} ${n === 1 ? singular : plural}`;
}
