/**
 * LyricsControlsCard - search, timing offset, size and reporting bad lyrics,
 * in priority order, on the stage rail.
 *
 * Named to avoid colliding with the library's LyricsCard. Saving goes through
 * useLyricsFixes, which the phone's More sheet calls too.
 */

import React, { useState } from "react";
import { Captions, FileText, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import LyricsFetchDialog from "@/features/lyrics/components/LyricsFetchDialog";
import PasteLyricsDialog from "@/features/lyrics/components/PasteLyricsDialog";
import { cn } from "@/lib/utils";
import { useLyricsFixes } from "../hooks/useLyricsFixes";
import LyricsOffsetRow from "./LyricsOffsetRow";
import LyricsReportRow from "./LyricsReportRow";
import LyricsSizeRow from "./LyricsSizeRow";
import { cardClass, cardIconClass, cardLabelClass } from "./cardStyles";

interface LyricsControlsCardProps {
  className?: string;
}

const LyricsControlsCard: React.FC<LyricsControlsCardProps> = ({
  className,
}) => {
  const fixes = useLyricsFixes();
  const { song, songForDialog } = fixes;

  const [isLyricsDialogOpen, setIsLyricsDialogOpen] = useState(false);
  const [isPasteLyricsDialogOpen, setIsPasteLyricsDialogOpen] = useState(false);

  return (
    <div className={cardClass(cn("shrink-0", className))}>
      <div className="flex items-center gap-2.5">
        <Captions className={cn(cardIconClass, "text-primary")} />
        <span className={cardLabelClass}>Lyrics</span>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          disabled={!song}
          onClick={() => setIsLyricsDialogOpen(true)}
          className="h-13 flex-1 text-lg font-semibold"
        >
          <Search className="mr-1 size-5" />
          Search
        </Button>
        <Button
          variant="outline"
          disabled={!song}
          onClick={() => setIsPasteLyricsDialogOpen(true)}
          aria-label="Paste lyrics"
          title="Paste lyrics"
          className="h-13 w-13 shrink-0"
        >
          <FileText className="size-5" />
        </Button>
      </div>

      <LyricsOffsetRow
        canSave={fixes.canSaveOffset}
        onSave={fixes.saveOffset}
        isSaving={fixes.isSaving}
      />
      <LyricsSizeRow />
      {fixes.hasLyrics && (
        <LyricsReportRow
          reported={fixes.reported}
          disabled={!fixes.songId || fixes.isReporting}
          onReport={fixes.report}
        />
      )}

      {songForDialog && (
        <>
          <LyricsFetchDialog
            isOpen={isLyricsDialogOpen}
            onClose={() => setIsLyricsDialogOpen(false)}
            song={songForDialog}
            onLyricsSelected={(result) =>
              fixes.applySearchResult(result, () =>
                setIsLyricsDialogOpen(false),
              )
            }
          />
          <PasteLyricsDialog
            isOpen={isPasteLyricsDialogOpen}
            onClose={() => setIsPasteLyricsDialogOpen(false)}
            onLyricsConfirmed={(text) =>
              fixes.applyPaste(text, () => setIsPasteLyricsDialogOpen(false))
            }
          />
        </>
      )}
    </div>
  );
};

export default LyricsControlsCard;
