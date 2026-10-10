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
  DeleteSongButton,
  FixPanels,
  SkipFingerprintButton,
  type FixPanel,
} from "./review/SongActions";
import { useReviewSong } from "./review/useReviewSong";

const STATUSES: FingerprintStatus[] = ["ambiguous", "no_match", "failed"];

const STATUS_LABEL: Record<FingerprintStatus, string> = {
  ambiguous: "Ambiguous",
  no_match: "No match",
  failed: "Lookup failed",
};

const STATUS_HELP: Record<FingerprintStatus, string> = {
  ambiguous: "AcoustID found more than one recording that could be this song.",
  no_match: "AcoustID doesn't know this recording.",
  failed: "The lookup itself failed, so it never got an answer.",
};

const STATUS_BADGE: Record<FingerprintStatus, string> = {
  ambiguous: "border-warning/50 text-warning-strong",
  no_match: "border-info/50 text-info-strong",
  failed: "border-destructive/50 text-destructive-strong",
};

// No match: AcoustID has nothing more to say, so search MusicBrainz instead.
const FIRST_PANEL: Record<FingerprintStatus, FixPanel> = {
  ambiguous: "fingerprint",
  no_match: "musicbrainz",
  failed: "fingerprint",
};

function isStatus(value: string | null): value is FingerprintStatus {
  return STATUSES.includes(value as FingerprintStatus);
}

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
        <SkipFingerprintButton songId={song.id} onSkipped={onDone} />
        <DeleteSongButton song={listed} onDeleted={onDone} />
      </FixPanels>
    </SongPanel>
  );
};

/** Songs AcoustID couldn't match with confidence. */
const AdminAcoustIdPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const param = searchParams.get("status");
  const status: FingerprintStatus = isStatus(param) ? param : "ambiguous";

  const queries: Record<
    FingerprintStatus,
    ReturnType<typeof useSongsByFingerprintStatus>
  > = {
    ambiguous: useSongsByFingerprintStatus("ambiguous"),
    no_match: useSongsByFingerprintStatus("no_match"),
    failed: useSongsByFingerprintStatus("failed"),
  };
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
          Songs AcoustID couldn&apos;t match with confidence. Fingerprinting the
          whole library is on the{" "}
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
