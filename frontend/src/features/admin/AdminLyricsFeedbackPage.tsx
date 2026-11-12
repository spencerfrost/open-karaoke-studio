import React, { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { MessageSquareHeart } from "lucide-react";
import {
  useLyricsFeedback,
  type SongLyricsFeedback,
} from "@/hooks/api/useLyricsFeedback";
import { FilterChips, ReviewEmpty, ReviewLayout } from "./review/ReviewLayout";
import { SongPanel } from "./review/SongPanel";
import { LyricsFixButtons } from "./review/SongActions";
import { describeWhen } from "./review/describeWhen";
import { useReviewSong } from "./review/useReviewSong";

type Filter = "off" | "spot-on" | "all";

const isOff = (entry: SongLyricsFeedback) => entry.wayOff + entry.aBitOff > 0;
const isSpotOn = (entry: SongLyricsFeedback) =>
  entry.spotOn > 0 && !isOff(entry);

/** "2 way off · 1 a bit off · 3 spot on", leaving out the zeros. */
function describeAnswers(entry: SongLyricsFeedback): string {
  const parts = [
    entry.wayOff && `${entry.wayOff} way off`,
    entry.aBitOff && `${entry.aBitOff} a bit off`,
    entry.spotOn && `${entry.spotOn} spot on`,
  ].filter(Boolean);
  return parts.length ? parts.join(" · ") : "No answers about these lyrics yet";
}

function describePlays(plays: number): string {
  return plays === 1 ? "sung once" : `sung ${plays} times`;
}

const FeedbackDetail: React.FC<{ entry: SongLyricsFeedback }> = ({ entry }) => {
  const queryClient = useQueryClient();
  const basics = {
    id: entry.songId,
    title: entry.title ?? entry.songId,
    artist: entry.artist ?? "",
  };
  const song = useReviewSong(basics);

  return (
    <SongPanel
      basics={basics}
      lyrics={{
        syncedLyrics: song.syncedLyrics,
        plainLyrics: song.plainLyrics,
      }}
      details={
        <div className="space-y-3">
          <div className="space-y-1 text-sm">
            <p>
              {describeAnswers(entry)}, last{" "}
              {describeWhen(entry.lastAnsweredAt)}
            </p>
            <p className="text-muted-foreground">
              {describePlays(entry.plays)}
              {entry.earlier > 0 &&
                ` · ${entry.earlier} older ${entry.earlier === 1 ? "answer" : "answers"} about lyrics or timings it no longer shows`}
              {entry.lyricsSource && ` · timings from ${entry.lyricsSource}`}
              {entry.lyricsHandPicked && " · picked by a person"}
            </p>
          </div>
        </div>
      }
    >
      {/* New lyrics start fresh: the answers so far move to "older". */}
      <LyricsFixButtons
        song={song}
        onSaved={() => {
          queryClient.invalidateQueries({ queryKey: ["songs"] });
          queryClient.invalidateQueries({ queryKey: ["lyrics", "feedback"] });
        }}
      />
    </SongPanel>
  );
};

/**
 * What singers said when the stage asked "How were the lyrics?" after their
 * song. Worst first: most "way off", then most "a bit off", then most sung.
 * Only answers about the lyrics and timings a song shows now are counted, so
 * a song drops off the list once its lyrics are fixed.
 */
const AdminLyricsFeedbackPage: React.FC = () => {
  const { data: entries, isLoading, error } = useLyricsFeedback();
  const [filter, setFilter] = useState<Filter>("off");

  const shown = entries?.filter((entry) =>
    filter === "off"
      ? isOff(entry)
      : filter === "spot-on"
        ? isSpotOn(entry)
        : true,
  );

  return (
    <ReviewLayout
      label="Lyrics feedback"
      items={shown}
      getId={(entry) => entry.songId}
      isLoading={isLoading}
      error={error}
      toolbar={
        <p className="text-sm text-muted-foreground">
          After each song the stage asks how the lyrics were. Nothing is fixed
          automatically: listen to the song, then find or paste better lyrics.
        </p>
      }
      filters={
        !!entries?.length && (
          <FilterChips
            label="Show songs"
            value={filter}
            onChange={(value) => setFilter(value as Filter)}
            chips={[
              {
                value: "off",
                label: "Off",
                count: entries.filter(isOff).length,
              },
              {
                value: "spot-on",
                label: "Spot on",
                count: entries.filter(isSpotOn).length,
              },
              { value: "all", label: "All", count: entries.length },
            ]}
          />
        )
      }
      empty={
        <ReviewEmpty icon={MessageSquareHeart} title="No answers here">
          After each song, the stage asks "How were the lyrics?".
        </ReviewEmpty>
      }
      renderRow={(entry) => (
        <>
          <p className="truncate text-sm font-medium">
            {entry.title ?? entry.songId}
          </p>
          <p className="truncate text-xs text-muted-foreground">
            {entry.artist}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {describeAnswers(entry)} · {describePlays(entry.plays)}
          </p>
        </>
      )}
      renderDetail={(entry) => <FeedbackDetail entry={entry} />}
    />
  );
};

export default AdminLyricsFeedbackPage;
