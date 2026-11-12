/**
 * LyricsFeedbackRow - "How were the lyrics?  [Spot on] [A bit off] [Way off]".
 *
 * Asked between songs, while whoever just sang still remembers. Unlike a
 * lyrics report it fixes nothing: the answers tell an admin which songs need
 * work, and which are right and must stay right. Ignoring it is fine, and
 * answering again changes the answer.
 */

import React from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  useAnswerLyricsFeedback,
  useLyricsFeedbackAnswer,
  type LyricsRating,
} from "@/hooks/api/useLyricsFeedback";
import { createLogger } from "@/lib/logger";
import { cn } from "@/lib/utils";

const logger = createLogger("component:lyrics-feedback-row");

const RATINGS: { rating: LyricsRating; label: string }[] = [
  { rating: "spot_on", label: "Spot on" },
  { rating: "a_bit_off", label: "A bit off" },
  { rating: "way_off", label: "Way off" },
];

interface LyricsFeedbackRowProps {
  /** The queue item that just finished. */
  queueItemId: number;
}

const LyricsFeedbackRow: React.FC<LyricsFeedbackRowProps> = ({
  queueItemId,
}) => {
  const answered = useLyricsFeedbackAnswer(queueItemId);
  const answer = useAnswerLyricsFeedback();

  const handleAnswer = (rating: LyricsRating) => {
    answer.mutate(
      { queueItemId, rating },
      {
        onError: (error) => {
          logger.error("Lyrics feedback failed:", error);
          toast.error("Couldn't save that", { description: error.message });
        },
      },
    );
  };

  return (
    <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-2">
      <p className="text-base text-foreground-dim">
        {answered ? "Thanks!" : "How were the lyrics?"}
      </p>
      <div className="flex items-center gap-2">
        {RATINGS.map(({ rating, label }) => {
          const isChosen = answered === rating;
          return (
            <Button
              key={rating}
              variant={isChosen ? "primary" : "outline"}
              onClick={() => handleAnswer(rating)}
              disabled={answer.isPending}
              aria-pressed={isChosen}
              className={cn(!isChosen && "text-foreground-dim")}
            >
              {label}
            </Button>
          );
        })}
      </div>
    </div>
  );
};

export default LyricsFeedbackRow;
