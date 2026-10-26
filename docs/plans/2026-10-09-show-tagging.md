# Show tagging for musicals

A song's show follows its MusicBrainz recording. It touches the MusicBrainz lookup, the
enrichment task, the artist credits rebuild, the song edit endpoint, one migration and the
rebuild's report dialog.

## Why

`show_name` exists so a song from a musical can be found under that show. "Seasons of Love"
should be under Rent. "Circle of Life" should be under The Lion King. The library's artist list
already shows shows next to artists (`/api/songs/shows`, folded in by
[useArtists.ts](../../frontend/src/hooks/api/useArtists.ts)). The idea is musicals, Broadway or
film. Songs that were just played in a movie are not the idea.

Prod on 2026-10-09 (read-only check): 8 songs are tagged, and 6 of those are wrong in that sense.

| Song | First released | Soundtrack it was tagged with |
|---|---|---|
| Bobcaygeon | 1998 | Trailer Park Boys: The Movie Soundtrack (2006) |
| A Case of You | 1971 | Practical Magic: Music From the Motion Picture (1998) |
| Swing, Swing | 2002 | American Pie: The Wedding: Music From the Motion Picture (2003) |
| Soul Meets Body | 2005 | Catch and Release (2007) |
| Beautiful Girls | 2007 | Cloverfield: Rob's Party Mix (2008) |
| A.M. 180 | 1997 | 28 Days Later: The Soundtrack Album (2002) |
| Circle of Life | 1994 | The Lion King: Original Motion Picture Soundtrack (1994) |
| When Your Mind's Made Up | 2007 | Once: Music From the Motion Picture (2007) |

Rent is missing even though "I'll Cover You (reprise)" has a MusicBrainz recording that sits on
the Rent soundtrack.

What's wrong, in [musicbrainz_service.py](../../backend/app/services/musicbrainz_service.py)
(`_extract_show_name`) and [metadata_tasks.py](../../backend/app/jobs/metadata_tasks.py):

1. **Any soundtrack counts.** If any release of the recording is in a release-group with the
   "Soundtrack" type, the song is tagged. Compilation and "Various Artists" soundtracks hold
   mostly licensed songs, so those get tagged too.
2. **Names keep their subtitles.** Only `(...)` is stripped, so names come out as "Rent:
   Original Motion Picture Soundtrack" instead of "Rent".
3. **A single can name the show.** For Circle of Life the first soundtrack release-group is the
   Elton John single called "Circle of Life", not the album.
4. **Nothing backfills.** Shows are only looked up inside `enrich_song_artist_credits`. Only
   these 8 songs have been through the lookup since the feature shipped.
5. **Automatic tags can't be told apart from hand-set ones.** The task fills `show_name` only
   when it's empty, so a manual edit survives, but a wrong automatic tag can never be corrected.
6. **A failed lookup looks like "no show".** `get_recording_details` returns `(None, None)` for
   both.

## The rule

Tag a song with a show only if its recording was **first released on the show's album**: a
release-group that is

- primary type "Album" (a single is named after the song, never the show),
- secondary type "Soundtrack" and not "Compilation" (MusicBrainz files Broadway cast albums as
  soundtracks too; there's no separate cast recording type),
- not credited to "Various Artists" on that release (a musical's album is credited to its
  composer or cast; Various Artists albums gather songs for a film, game or TV series),
- first released the same **year** as the recording.

A song written for a show comes out on the show's album. A licensed song came out years earlier
on the artist's own album. Years rather than dates let a lead single out weeks before the album
still count. Of the albums that qualify, the one out on the recording's exact first release date
wins (the original over a same-year translated edition like "O Rei Leão"), then the earliest.

Names lose `(...)` and an album-kind subtitle after ": " or " - " ("Original Motion Picture
Soundtrack", "Music From the Motion Picture", "Original Broadway Cast Recording", "The Soundtrack
Album", "Season Two Original Soundtrack" …). Only those phrases go; "Spider-Man: Turn Off the
Dark" keeps its colon.

Checked on dev's 1,056 cached recordings (2026-10-26): the rule tags Wicked, The Lion King,
Rent, Once, Man of La Mancha and The Pick of Destiny. Without the album, compilation and Various
Artists checks it also tagged about 20 game, TV-mix and licensed-cover songs (Burnout 3,
Smallville, Shrek's "Hallelujah", Pleasantville…).

Known edges, accepted:

- A song written for a film or series that isn't a musical passes: TRON: Ares, Before the Flood,
  Bones and All and Arcane on dev, "My Heart Will Go On" in general. People think of those as
  "from" the film.
- Film musicals whose album is credited to Various Artists are missed: Across the Universe on
  dev. Set those by hand.
- A pop cover of a show song (a later recording on the artist's own album) fails.
- Songs with no recording ID can't be tagged automatically. The show name field in the song
  details dialog
  ([DetailsTab.tsx](../../frontend/src/features/songs/components/song-details/tabs/DetailsTab.tsx))
  covers them.
- "Ambiguous" AcoustID songs have a recording picked by the tiebreak, which may be a different
  recording of the same song. "Falling Slowly" is the example: the Once soundtrack recording
  (`8375aa24…`, 2007) passes and The Swell Season album one (`8e2a859c…`, 2006) fails.

## How it's built

### Show lookup

`_extract_show_name` in [musicbrainz_service.py](../../backend/app/services/musicbrainz_service.py)
applies the rule above. `get_recording_details` returns `None` when the lookup fails, so a
failure never clears a show. Tests run the rule on trimmed real MusicBrainz responses in
`backend/tests/fixtures/musicbrainz/` (Bobcaygeon, Circle of Life, the Rent reprise, Defying
Gravity, both Falling Slowly recordings).

### Hand-set shows

`songs.show_name_hand_set_at`, like `album_hand_set_at`. The song details edit sets it whenever a
person changes the show, including clearing it: a hand-cleared show keeps the song out of every
show. Existing rows start unmarked.

### One writer

`store_detected_show` in
[show_name_service.py](../../backend/app/services/show_name_service.py) writes the show a
recording points to, `None` clearing it, and skips hand-set songs. It's called from:

- `enrich_song_artist_credits`, which every path that links a recording already runs (single
  fingerprint, batch fingerprint, admin pick). A song without a recording loses its show.
- The artist credits rebuild, which already looks up every linked recording. It sets every
  song's show from that lookup, and the report gets a **Shows** tab listing each change (before
  and after) and a "Songs from a show" count.

Paths that drop a recording (AcoustID suggesting a different song, no match, a person editing
the title or artist) clear the show with it unless it was hand-set.

There's no separate show task, backfill job or admin button: refreshing shows across the library
is a rebuild run, and its preview shows every change before it's applied.

## Rollout

- Dev: migration applied. Restart Celery, run the artist credits rebuild preview, read the Shows
  tab.
- Prod: the rebuild was already pending. Migration, Celery restart, rebuild preview (check the
  Shows tab: the 6 licensed tags clear, Rent appears), pg_dump, apply.
- Afterwards, set by hand anything the rule misses (Across the Universe, and "Falling Slowly" if
  its recording is the Swell Season one or missing).

## Not in this plan

- Stripping "Artist - " prefixes from YouTube titles (better MB search hits). Separate small
  fix, raised 2026-10-09 with the credits resolver change.
- Tagging songs with no recording ID from other signals (YouTube title "from Rent", artist
  "Original Broadway Cast of …"). Revisit if the manual field turns out to be too much work.
