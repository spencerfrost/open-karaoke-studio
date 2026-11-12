import React from "react";
import { Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  useRunReport,
  type ArtistCreditsReport,
  type LibraryNumbers,
  type ReportCredit,
  type ReportSong,
} from "./hooks/useBatchJobs";

/** "A & B feat. C, D", the way a song's artist line reads. */
const creditLine = (credits: ReportCredit[]): string => {
  const primaries = credits.filter((c) => c.role === "primary");
  const featured = credits.filter((c) => c.role === "featured");
  const line = primaries.map((c) => c.name).join(" & ");
  return featured.length > 0
    ? `${line} feat. ${featured.map((c) => c.name).join(", ")}`
    : line;
};

const NUMBER_LABEL: Record<keyof LibraryNumbers, string> = {
  songs: "Songs",
  songsWithRecording: "Songs linked to a MusicBrainz recording",
  artists: "Artists",
  artistsLinked: "Artists credited on a song",
  artistsLinkedToNothing: "Artists credited on nothing",
  featuredOnly: "Artists only ever featured",
  featuredOnlyOnOneSong: "…featured on a single song",
  groupedGuestCredits: "Featured credits naming two artists (“A & B”)",
  featInTitle: "Songs with “(feat. …)” in the title",
  aliases: "Other names artists go by",
  songsWithShow: "Songs from a show",
};

const Count: React.FC<{ n: number }> = ({ n }) => (
  <span className="ml-1.5 tabular-nums text-muted-foreground">
    {n.toLocaleString()}
  </span>
);

/** A cut-down list says so, since the counts are always whole. */
const Shown: React.FC<{ shown: number; of: number }> = ({ shown, of }) =>
  shown < of ? (
    <p className="text-xs text-muted-foreground">
      Showing the first {shown.toLocaleString()} of {of.toLocaleString()}.
    </p>
  ) : null;

const SongList: React.FC<{
  songs: ReportSong[];
  count: number;
  empty: string;
}> = ({ songs, count, empty }) =>
  songs.length === 0 ? (
    <p className="text-sm text-muted-foreground">{empty}</p>
  ) : (
    <>
      <Shown shown={songs.length} of={count} />
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Song</TableHead>
            <TableHead>Artist line</TableHead>
            <TableHead>Credits</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {songs.map((song) => (
            <TableRow key={song.songId}>
              <TableCell>{song.title}</TableCell>
              <TableCell>{song.artist}</TableCell>
              <TableCell>{creditLine(song.credits)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </>
  );

/** Songs whose show the run changes. */
const ShowChanges: React.FC<{
  shows: NonNullable<ArtistCreditsReport["shows"]>;
}> = ({ shows }) => (
  <TabsContent value="shows" className="space-y-2">
    <p className="text-sm text-muted-foreground">
      Songs whose show changes to the one their recording first came out on.
      Shows set by hand stay as they are
      {(shows.counts.hand_set ?? 0) > 0 && ` (${shows.counts.hand_set})`}; fix a
      wrong one from the song's details.
    </p>
    <Shown shown={shows.changed.length} of={shows.counts.changed ?? 0} />
    {shows.changed.length === 0 ? (
      <p className="text-sm text-muted-foreground">No changes.</p>
    ) : (
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Song</TableHead>
            <TableHead>Show before</TableHead>
            <TableHead>Show after</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {shows.changed.map((song) => (
            <TableRow key={song.songId}>
              <TableCell>
                <div>{song.title}</div>
                <div className="text-xs text-muted-foreground">
                  {song.artist}
                </div>
              </TableCell>
              <TableCell className="text-muted-foreground">
                {song.before ?? "None"}
              </TableCell>
              <TableCell>{song.after ?? "None"}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    )}
  </TabsContent>
);

/**
 * What an artist credits run changed, or would change: a preview's report is
 * the one to read before applying.
 */
const ArtistCreditsReportDialog: React.FC<{
  runId: number | null;
  onOpenChange: (open: boolean) => void;
}> = ({ runId, onOpenChange }) => {
  const { data, isLoading, error } = useRunReport(runId);
  const report = data?.report;

  return (
    <Dialog open={runId !== null} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-5xl">
        <DialogHeader>
          <DialogTitle>
            Artist credits {report?.mode === "apply" ? "changes" : "preview"}
          </DialogTitle>
          <DialogDescription>
            {report?.mode === "apply"
              ? "What this run changed."
              : "What applying would change. Nothing has changed yet."}
          </DialogDescription>
        </DialogHeader>

        {isLoading && <Loader2 className="mx-auto size-6 animate-spin" />}
        {error && (
          <p className="text-sm text-destructive">
            Couldn't load the report: {error.message}
          </p>
        )}

        {report && (
          <Tabs defaultValue="numbers">
            <TabsList className="flex-wrap">
              <TabsTrigger value="numbers">Numbers</TabsTrigger>
              <TabsTrigger value="songs">
                Songs
                <Count n={report.songs.counts.changed ?? 0} />
              </TabsTrigger>
              <TabsTrigger value="merges">
                Merges
                <Count n={report.merges.length} />
              </TabsTrigger>
              <TabsTrigger value="renames">
                Renames
                <Count n={report.renames.length} />
              </TabsTrigger>
              <TabsTrigger value="deleted">
                Removed
                <Count n={report.deleted.count} />
              </TabsTrigger>
              <TabsTrigger value="unsure">
                Unsure
                <Count n={report.unsure.count} />
              </TabsTrigger>
              <TabsTrigger value="disagree">
                Disagree
                <Count n={report.disagree.count} />
              </TabsTrigger>
              {report.shows && (
                <TabsTrigger value="shows">
                  Shows
                  <Count n={report.shows.counts.changed ?? 0} />
                </TabsTrigger>
              )}
            </TabsList>

            <TabsContent value="numbers" className="space-y-3">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead />
                    <TableHead className="text-right">Before</TableHead>
                    <TableHead className="text-right">After</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(Object.keys(NUMBER_LABEL) as (keyof LibraryNumbers)[]).map(
                    (key) => (
                      <TableRow key={key}>
                        <TableCell>{NUMBER_LABEL[key]}</TableCell>
                        <TableCell className="text-right tabular-nums">
                          {report.before[key]?.toLocaleString() ?? "–"}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {report.after[key]?.toLocaleString() ?? "–"}
                        </TableCell>
                      </TableRow>
                    ),
                  )}
                </TableBody>
              </Table>
              <p className="text-sm text-muted-foreground">
                {(report.songs.counts.recording ?? 0).toLocaleString()} songs
                credited from their recording,{" "}
                {(report.songs.counts.parsed ?? 0).toLocaleString()} re-read
                from their artist line,{" "}
                {(report.songs.counts.kept ?? 0).toLocaleString()} kept as they
                were.
                {(report.songs.counts.lookup_failed ?? 0) > 0 &&
                  ` ${report.songs.counts.lookup_failed} recording lookups failed; running it again retries them.`}
              </p>
            </TabsContent>

            <TabsContent value="songs" className="space-y-2">
              <Shown
                shown={report.songs.changed.length}
                of={report.songs.counts.changed ?? 0}
              />
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Song</TableHead>
                    <TableHead>Credits before</TableHead>
                    <TableHead>Credits after</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {report.songs.changed.map((song) => (
                    <TableRow key={song.songId}>
                      <TableCell>
                        <div>{song.title}</div>
                        <div className="text-xs text-muted-foreground">
                          {song.artist}
                        </div>
                        <div className="mt-1 flex gap-1">
                          {song.confirmed && (
                            <Badge variant="outline">Confirmed</Badge>
                          )}
                          {song.source === "parsed" && (
                            <Badge variant="outline">From artist line</Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {creditLine(song.before) || "None"}
                      </TableCell>
                      <TableCell>{creditLine(song.after)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TabsContent>

            <TabsContent value="merges">
              {report.merges.length === 0 ? (
                <p className="text-sm text-muted-foreground">No merges.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Artist</TableHead>
                      <TableHead>Merged into</TableHead>
                      <TableHead>Because</TableHead>
                      <TableHead className="text-right">
                        Credits moved
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {report.merges.map((merge, i) => (
                      <TableRow key={i}>
                        <TableCell>{merge.from}</TableCell>
                        <TableCell>{merge.into}</TableCell>
                        <TableCell>
                          {merge.reason === "musicbrainz"
                            ? "MusicBrainz lists it as their name"
                            : "Same name, spelled differently"}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {merge.credits}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </TabsContent>

            <TabsContent value="renames">
              {report.renames.length === 0 ? (
                <p className="text-sm text-muted-foreground">No renames.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Was</TableHead>
                      <TableHead>Now</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {report.renames.map((rename, i) => (
                      <TableRow key={i}>
                        <TableCell>{rename.from}</TableCell>
                        <TableCell>{rename.to}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </TabsContent>

            <TabsContent value="deleted" className="space-y-2">
              <p className="text-sm text-muted-foreground">
                Artists no song, album or credit refers to any more.
              </p>
              <Shown
                shown={report.deleted.names.length}
                of={report.deleted.count}
              />
              <p className="text-sm">{report.deleted.names.join(", ")}</p>
            </TabsContent>

            <TabsContent value="unsure" className="space-y-2">
              <p className="text-sm text-muted-foreground">
                Songs without a MusicBrainz recording whose artist has “&” or
                “and” in it. It's left as one artist unless both halves are
                artists already; split any that are two with Manage Collabs.
              </p>
              <SongList
                songs={report.unsure.songs}
                count={report.unsure.count}
                empty="None."
              />
            </TabsContent>

            <TabsContent value="disagree" className="space-y-2">
              <p className="text-sm text-muted-foreground">
                Songs whose credits don't name the artist in their artist line.
                Usually a mislabelled song or recording; fix it from the song's
                details.
              </p>
              <SongList
                songs={report.disagree.songs}
                count={report.disagree.count}
                empty="None."
              />
            </TabsContent>

            {report.shows && <ShowChanges shows={report.shows} />}
          </Tabs>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default ArtistCreditsReportDialog;
