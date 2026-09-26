import { describe, expect, it } from "vitest";
import type { Artist } from "@/hooks/api/useArtists";
import {
  LETTERS,
  artistImageUrl,
  columnBrightness,
  columnSeats,
  firstArtistByLetter,
  holdRate,
  listScrollOffset,
  lyricsKind,
  songByline,
  songHeroSources,
  songYear,
  stepLetter,
  tileInitial,
  toWheelArtists,
  vocalRange,
  WHEEL_TUNING,
} from "./wheelModel";

const artist = (name: string, firstLetter: string, id = 0): Artist => ({
  id,
  name,
  sortName: name.toLowerCase(),
  songCount: 1,
  firstLetter,
});

const letter = (l: string) => LETTERS.indexOf(l as (typeof LETTERS)[number]);

describe("toWheelArtists", () => {
  it("groups by letter so each letter's artists are contiguous", () => {
    const wheel = toWheelArtists([
      artist("ABBA", "A"),
      artist("Øystein", "#"),
      artist("Beck", "B"),
      artist("3 Doors Down", "#"),
    ]);
    expect(wheel.map((a) => a.name)).toEqual([
      "Øystein",
      "3 Doors Down",
      "ABBA",
      "Beck",
    ]);
  });

  it("files an unknown letter under #", () => {
    expect(toWheelArtists([artist("?", "?")])[0].letterIndex).toBe(0);
  });
});

describe("stepLetter", () => {
  const wheel = toWheelArtists([
    artist("ABBA", "A"),
    artist("Adele", "A"),
    artist("Beck", "B"),
    artist("Dido", "D"),
  ]);
  const first = firstArtistByLetter(wheel);

  it("lands on the first artist of the next letter", () => {
    expect(stepLetter(1, 1, wheel, first)).toBe(2);
  });

  it("skips letters with no artists", () => {
    expect(first[letter("C")]).toBe(-1);
    expect(stepLetter(2, 1, wheel, first)).toBe(3);
  });

  it("goes back to the first artist of the previous letter", () => {
    expect(stepLetter(3, -1, wheel, first)).toBe(2);
    expect(stepLetter(2, -1, wheel, first)).toBe(0);
  });

  it("stops at either end", () => {
    expect(stepLetter(0, -1, wheel, first)).toBeNull();
    expect(stepLetter(3, 1, wheel, first)).toBeNull();
  });
});

describe("geometry", () => {
  it("puts artists at the front, letters left and songs right", () => {
    const [l, a, s] = columnSeats();
    expect(a).toBe(0);
    expect(l).toBeLessThan(0);
    expect(s).toBeGreaterThan(0);
  });

  it("seats the narrow letter column closer than the wide song column", () => {
    const [l, , s] = columnSeats();
    expect(Math.abs(l)).toBeLessThan(Math.abs(s));
  });

  it("compounds dimming per step back", () => {
    expect(columnBrightness(0)).toBe(1);
    expect(columnBrightness(2)).toBeCloseTo(WHEEL_TUNING.sideBrightness ** 2);
  });
});

describe("holdRate", () => {
  it("ramps from the start rate to the top rate and holds there", () => {
    expect(holdRate(-100)).toBe(WHEEL_TUNING.holdStartRate);
    expect(holdRate(0)).toBe(WHEEL_TUNING.holdStartRate);
    expect(holdRate(WHEEL_TUNING.holdRampMs)).toBe(WHEEL_TUNING.holdTopRate);
    expect(holdRate(10_000)).toBe(WHEEL_TUNING.holdTopRate);
  });
});

describe("artwork", () => {
  it("asks for artist photos by name, and never for shows", () => {
    expect(artistImageUrl({ name: "AC/DC" })).toBe(
      "/api/artists/image?name=AC%2FDC",
    );
    expect(artistImageUrl({ name: "Wicked", isShow: true })).toBeNull();
  });

  it("leads the hero with the stored still, then YouTube, then the cover", () => {
    expect(
      songHeroSources({
        id: "s1",
        thumbnail: "thumbnail.webp",
        videoId: "abc",
        albumCoverUrl: "/api/albums/4/cover",
      }),
    ).toEqual([
      "/api/songs/s1/thumbnail",
      "https://img.youtube.com/vi/abc/hqdefault.jpg",
      "/api/albums/4/cover",
    ]);
    expect(songHeroSources({ id: "s2" })).toEqual([]);
  });

  it("drops a leading article from the tile letter", () => {
    expect(tileInitial("The Cure")).toBe("C");
    expect(tileInitial("a-ha")).toBe("A");
    expect(tileInitial("The")).toBe("T");
    expect(tileInitial("édith piaf")).toBe("É");
    expect(tileInitial("  ")).toBe("?");
  });

  it("adds featured artists the artist string doesn't already name", () => {
    const artists = [
      { id: 1, name: "Mark Ronson", role: "primary" as const },
      { id: 2, name: "Bruno Mars", role: "featured" as const },
    ];
    expect(songByline({ artist: "Mark Ronson", artists })).toBe(
      "Mark Ronson feat. Bruno Mars",
    );
    expect(songByline({ artist: "Mark Ronson ft. Bruno Mars", artists })).toBe(
      "Mark Ronson ft. Bruno Mars",
    );
  });

  it("names the best lyrics a song has", () => {
    expect(lyricsKind({ wordSyncedLyrics: "x", syncedLyrics: "y" })).toBe(
      "word-synced",
    );
    expect(lyricsKind({ syncedLyrics: "y", plainLyrics: "z" })).toBe("synced");
    expect(lyricsKind({ plainLyrics: "z" })).toBe("plain");
    expect(lyricsKind({ wordSyncedLyrics: null })).toBe("none");
  });

  it("leaves out facts that are only half known", () => {
    expect(vocalRange({ vocalRangeLow: "G3", vocalRangeHigh: "D4" })).toBe(
      "G3–D4",
    );
    expect(vocalRange({ vocalRangeLow: "G3" })).toBeNull();
    expect(songYear({ year: 1977 })).toBe(1977);
    expect(songYear({ releaseDate: "1977-02-04T08:00:00Z" })).toBe(1977);
    expect(songYear({ releaseDate: "unknown" })).toBeNull();
    expect(songYear({})).toBeNull();
  });
});

describe("listScrollOffset", () => {
  // 10 rows of 50px in a 200px column: 4 rows visible, max offset 300.
  const offset = (cursor: number, count = 10) =>
    listScrollOffset(cursor, count, 50, 200);

  it("keeps the list at the top until the cursor passes the middle", () => {
    expect(offset(0)).toBe(0);
    expect(offset(1)).toBe(0);
    expect(offset(2)).toBe(25);
  });

  it("centres the cursor in the middle of the list", () => {
    expect(offset(5)).toBe(5 * 50 + 25 - 100);
  });

  it("stops with the last row at the bottom of the column", () => {
    expect(offset(8)).toBe(300);
    expect(offset(9)).toBe(300);
  });

  it("never scrolls a list shorter than the column", () => {
    expect(offset(0, 3)).toBe(0);
    expect(offset(2, 3)).toBe(0);
  });
});
