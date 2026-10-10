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
  song_albums: {
    name: "Album covers",
    description:
      "Finds each song's album and cover on YouTube Music from the exact video it was downloaded from, or on Deezer when that fails.",
    unit: ["song", "songs"],
  },
  fingerprint: {
    name: "AcoustID fingerprints",
    description:
      "Identifies each song from its audio and links it to MusicBrainz. A song AcoustID names differently goes to the AcoustID page for review; nothing is renamed automatically.",
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
