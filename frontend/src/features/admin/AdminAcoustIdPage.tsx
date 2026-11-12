import React from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { Fingerprint } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { Song } from "@/types/Song";
import {
  ACOUSTID_SONGS_KEY,
  useSongsByFingerprintStatus,
  type FingerprintStatus,
} from "./hooks/useAdminQueries";
import {
  FilterChips,
  ReviewEmpty,
  ReviewLayout,
  type ReviewSelection,
} from "./review/ReviewLayout";
import { SongPanel } from "./review/SongPanel";
import {
  AcceptSuggestionButton,
  DeleteSongButton,
  FixPanels,
  SkipFingerprintButton,
  type FixPanel,
} from "./review/SongActions";
import { useReviewSong } from "./review/useReviewSong";

const STATUSES: FingerprintStatus[] = [
  "suggested",
  "ambiguous",
  "no_match",
  "failed",
];

const STATUS_LABEL: Record<FingerprintStatus, string> = {
  suggested: "Different name",
  ambiguous: "Ambiguous",
  no_match: "No match",
  failed: "Lookup failed",
};

const STATUS_HELP: Record<FingerprintStatus, string> = {
  suggested: "AcoustID recognised the audio but names the song differently.",
  ambiguous: "AcoustID found more than one recording that could be this song.",
  no_match: "AcoustID doesn't know this recording.",
  failed: "The lookup itself failed, so it never got an answer.",
};

const STATUS_BADGE: Record<FingerprintStatus, string> = {
  suggested: "border-success/50 text-success-strong",
  ambiguous: "border-warning/50 text-warning-strong",
  no_match: "border-info/50 text-info-strong",
  failed: "border-destructive/50 text-destructive-strong",
};

// No match: AcoustID has nothing more to say, so search MusicBrainz instead.
// Different name: the comparison comes first, with no fix open.
const FIRST_PANEL: Record<FingerprintStatus, FixPanel | undefined> = {
  suggested: undefined,
  ambiguous: "fingerprint",
  no_match: "musicbrainz",
  failed: "fingerprint",
};

function isStatus(value: string | null): value is FingerprintStatus {
  return STATUSES.includes(value as FingerprintStatus);
}

/** The song's details now beside what AcoustID would call it. */
const SuggestionCompare: React.FC<{
  song: Song;
  onDone: () => void;
}> = ({ song, onDone }) => {
  const suggestion = song.acoustidSuggestion;
  if (!suggestion) return null;
  const rows = [
    { label: "Title", now: song.title, suggested: suggestion.title },
    { label: "Artist", now: song.artist, suggested: suggestion.artist },
  ];

  return (
    <div className="space-y-3 rounded-md border p-3">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-muted-foreground">
            <th className="w-16 pb-1 font-normal" />
            <th className="pb-1 font-normal">Now</th>
            <th className="pb-1 font-normal">AcoustID suggests</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.label} className="align-top">
              <td className="py-0.5 text-muted-foreground">{row.label}</td>
              <td className="py-0.5 pr-3">{row.now}</td>
              <td
                className={cn(
                  "py-0.5",
                  row.suggested !== row.now && "font-medium",
                )}
              >
                {row.suggested ?? "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="flex flex-wrap gap-2">
        <AcceptSuggestionButton songId={song.id} onAccepted={onDone} />
        <SkipFingerprintButton songId={song.id} onSkipped={onDone} />
      </div>
    </div>
  );
};

const AcoustIdDetail: React.FC<{
  song: Song;
  status: FingerprintStatus;
  selection: ReviewSelection;
}> = ({ song: listed, status, selection }) => {
  const queryClient = useQueryClient();
  const song = useReviewSong(listed);

  const onDone = () => {
    selection.done();
    queryClient.invalidateQueries({ queryKey: [ACOUSTID_SONGS_KEY] });
    queryClient.invalidateQueries({ queryKey: ["songs"] });
  };

  return (
    <SongPanel
      basics={listed}
      details={
        <p className="text-sm">
          <Badge variant="outline" className={cn("mr-2", STATUS_BADGE[status])}>
            {STATUS_LABEL[status]}
          </Badge>
          {listed.acoustidScore != null &&
            `Best match ${Math.round(listed.acoustidScore * 100)}%. `}
          <span className="text-muted-foreground">{STATUS_HELP[status]}</span>
        </p>
      }
    >
      {status === "suggested" && (
        <SuggestionCompare song={listed} onDone={onDone} />
      )}
      <FixPanels
        song={song}
        open={FIRST_PANEL[status]}
        panels={[
          "fingerprint",
          "musicbrainz",
          "edit",
          "replace-yt",
          "replace-upload",
        ]}
        onDone={onDone}
      >
        {status !== "suggested" && (
          <SkipFingerprintButton songId={song.id} onSkipped={onDone} />
        )}
        <DeleteSongButton song={listed} onDeleted={onDone} />
      </FixPanels>
    </SongPanel>
  );
};

/** Songs AcoustID named differently, or couldn't match with confidence. */
const AdminAcoustIdPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const param = searchParams.get("status");

  const queries: Record<
    FingerprintStatus,
    ReturnType<typeof useSongsByFingerprintStatus>
  > = {
    suggested: useSongsByFingerprintStatus("suggested"),
    ambiguous: useSongsByFingerprintStatus("ambiguous"),
    no_match: useSongsByFingerprintStatus("no_match"),
    failed: useSongsByFingerprintStatus("failed"),
  };
  // Without a choice in the URL, open the first list that has songs in it.
  const status: FingerprintStatus = isStatus(param)
    ? param
    : (STATUSES.find((s) => queries[s].data?.length) ?? "suggested");
  const active = queries[status];

  return (
    <ReviewLayout
      label={`AcoustID: ${STATUS_LABEL[status]}`}
      items={active.data}
      getId={(song) => song.id}
      isLoading={active.isLoading}
      error={active.error}
      toolbar={
        <p className="text-sm text-muted-foreground">
          Songs AcoustID names differently, or couldn&apos;t match with
          confidence. AcoustID never renames a song by itself. Fingerprinting
          the whole library is on the{" "}
          <Link to="/admin/jobs" className="underline">
            Background jobs
          </Link>{" "}
          page.
        </p>
      }
      filters={
        <FilterChips
          label="Show songs"
          value={status}
          // A new list: drop the selected song with the old filter.
          onChange={(value) => setSearchParams({ status: value })}
          chips={STATUSES.map((s) => ({
            value: s,
            label: STATUS_LABEL[s],
            count: queries[s].data?.length,
          }))}
        />
      }
      empty={
        <ReviewEmpty icon={Fingerprint} title="Nothing here">
          No songs are &ldquo;{STATUS_LABEL[status].toLowerCase()}&rdquo;.
        </ReviewEmpty>
      }
      renderRow={(song) => (
        <div className="flex items-center gap-3">
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{song.title}</p>
            <p className="truncate text-xs text-muted-foreground">
              {song.artist}
            </p>
          </div>
          {song.acoustidScore != null && (
            <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
              {Math.round(song.acoustidScore * 100)}%
            </span>
          )}
        </div>
      )}
      renderDetail={(song, selection) => (
        <AcoustIdDetail song={song} status={status} selection={selection} />
      )}
    />
  );
};

export default AdminAcoustIdPage;
