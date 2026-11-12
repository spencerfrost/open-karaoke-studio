import React, { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ShieldAlert } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { createLogger } from "@/lib/logger";
import { cn } from "@/lib/utils";
import {
  useMetadataAudit,
  type FlaggedSong,
  type Severity,
} from "./hooks/useAdminQueries";
import {
  FilterChips,
  ReviewEmpty,
  ReviewLayout,
  type ReviewSelection,
} from "./review/ReviewLayout";
import { SongPanel } from "./review/SongPanel";
import {
  AnalyzeVocalRangeButton,
  DeleteSongButton,
  FixPanels,
  LyricsFixButtons,
  type FixPanel,
} from "./review/SongActions";
import { useReviewSong } from "./review/useReviewSong";

const logger = createLogger("component:AdminMetadataPage");

const SEVERITY_BADGE: Record<Severity, string> = {
  error: "border-destructive/50 text-destructive-strong",
  warning: "border-warning/50 text-warning-strong",
  info: "border-muted-foreground/50 text-muted-foreground",
};

type IssueFix = FixPanel | "lyrics" | "vocal-range";

// What can fix each kind of issue.
const ISSUE_FIXES: Record<string, IssueFix[]> = {
  empty_title: ["edit"],
  empty_artist: ["edit"],
  suspicious_title: ["edit", "musicbrainz", "replace-yt"],
  long_title: ["edit"],
  swapped_fields: ["edit"],
  encoding_artifact: ["edit"],
  unknown_artist: ["edit", "musicbrainz"],
  missing_source: ["replace-yt", "replace-upload"],
  missing_duration: ["replace-yt", "replace-upload"],
  missing_album: ["edit", "musicbrainz", "fingerprint"],
  missing_lyrics: ["lyrics"],
  missing_vocal_range: ["vocal-range"],
};

const PANEL_ORDER: FixPanel[] = [
  "edit",
  "musicbrainz",
  "fingerprint",
  "replace-yt",
  "replace-upload",
];

const MetadataDetail: React.FC<{
  flagged: FlaggedSong;
  onFixed: () => void;
}> = ({ flagged, onFixed }) => {
  const song = useReviewSong(flagged);
  const fixes = new Set(
    flagged.issues.flatMap((issue) => ISSUE_FIXES[issue.type] ?? []),
  );
  const panels = PANEL_ORDER.filter((panel) => fixes.has(panel));

  return (
    <SongPanel
      basics={flagged}
      details={
        <div className="flex flex-wrap gap-1.5">
          {flagged.issues.map((issue) => (
            <Badge
              key={issue.type}
              variant="outline"
              className={SEVERITY_BADGE[issue.severity]}
            >
              {issue.label}
            </Badge>
          ))}
        </div>
      }
    >
      <FixPanels
        song={song}
        panels={panels}
        open={panels.length === 1 ? panels[0] : undefined}
        onDone={onFixed}
      >
        {fixes.has("lyrics") && (
          <LyricsFixButtons song={song} onSaved={onFixed} />
        )}
        {fixes.has("vocal-range") && (
          <AnalyzeVocalRangeButton songId={song.id} onDone={onFixed} />
        )}
        <DeleteSongButton song={flagged} onDeleted={onFixed} />
      </FixPanels>
    </SongPanel>
  );
};

/** Songs with missing or suspicious details, from a scan run by hand. */
const AdminMetadataPage: React.FC = () => {
  const queryClient = useQueryClient();
  const scanQuery = useMetadataAudit();
  const result = scanQuery.data;
  const [issueType, setIssueType] = useState("all");

  const runScan = async () => {
    const { data, isError } = await scanQuery.refetch();
    if (isError || !data) {
      toast.error("Couldn't run the metadata scan");
      return;
    }
    setIssueType("all");
    logger.info("Metadata scan complete", {
      scanned: data.total_songs_scanned,
      flagged: data.total_flagged,
    });
  };

  const issueChips = useMemo(() => {
    const byType = new Map<string, { label: string; count: number }>();
    for (const song of result?.flagged_songs ?? []) {
      for (const issue of song.issues) {
        const chip = byType.get(issue.type);
        if (chip) chip.count += 1;
        else byType.set(issue.type, { label: issue.label, count: 1 });
      }
    }
    return [...byType.entries()]
      .sort(
        ([, a], [, b]) => b.count - a.count || a.label.localeCompare(b.label),
      )
      .map(([value, { label, count }]) => ({ value, label, count }));
  }, [result]);

  // The last song with that issue fixed: back to everything.
  const filter = issueChips.some((chip) => chip.value === issueType)
    ? issueType
    : "all";

  const shown = useMemo(
    () =>
      filter === "all"
        ? result?.flagged_songs
        : result?.flagged_songs.filter((song) =>
            song.issues.some((issue) => issue.type === filter),
          ),
    [result, filter],
  );

  const onFixed = (selection: ReviewSelection) => {
    selection.done();
    queryClient.invalidateQueries({ queryKey: ["songs"] });
    // Scan again quietly so the fixed song drops off the list.
    scanQuery.refetch();
  };

  return (
    <ReviewLayout
      label="Songs with metadata issues"
      items={shown}
      getId={(song) => song.id}
      isLoading={scanQuery.isFetching && !result}
      toolbar={
        <div className="flex flex-wrap items-center justify-between gap-4">
          <p className="text-sm text-muted-foreground">
            {result
              ? `${result.total_flagged} of ${result.total_songs_scanned} songs have missing or suspicious details.`
              : "Scan the library for songs with missing or suspicious details."}
          </p>
          <Button onClick={runScan} disabled={scanQuery.isFetching}>
            <ShieldAlert className="mr-2 h-4 w-4" />
            {scanQuery.isFetching
              ? "Scanning…"
              : result
                ? "Scan again"
                : "Run scan"}
          </Button>
        </div>
      }
      filters={
        issueChips.length > 0 && (
          <FilterChips
            label="Show issues"
            value={filter}
            onChange={setIssueType}
            chips={[
              {
                value: "all",
                label: "All",
                count: result?.flagged_songs.length,
              },
              ...issueChips,
            ]}
          />
        )
      }
      empty={
        result ? (
          <ReviewEmpty icon={ShieldAlert} title="All clear">
            No metadata issues found.
          </ReviewEmpty>
        ) : (
          <ReviewEmpty icon={ShieldAlert}>
            Run a scan to check every song&apos;s details.
          </ReviewEmpty>
        )
      }
      renderRow={(song) => {
        const worst = song.issues.find((i) => i.severity === "error")
          ? "error"
          : song.issues.find((i) => i.severity === "warning")
            ? "warning"
            : "info";
        return (
          <>
            <p className="truncate text-sm font-medium">{song.title}</p>
            <p className="truncate text-xs text-muted-foreground">
              {song.artist}
            </p>
            <p
              className={cn(
                "mt-1 truncate text-xs",
                worst === "error"
                  ? "text-destructive-strong"
                  : worst === "warning"
                    ? "text-warning-strong"
                    : "text-muted-foreground",
              )}
            >
              {song.issues.map((issue) => issue.label).join(" · ")}
            </p>
          </>
        );
      }}
      renderDetail={(song, selection) => (
        <MetadataDetail flagged={song} onFixed={() => onFixed(selection)} />
      )}
    />
  );
};

export default AdminMetadataPage;
