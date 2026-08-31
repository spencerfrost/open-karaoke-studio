/**
 * RosterPicker - "who's singing?" as a grid of big name buttons.
 *
 * Lifted out of SongConfirmScreen, which promised this second caller in its own
 * doc comment: unit 4's handoff screen asks the same question when someone taps
 * "That's not me", and a walk-up on a TV should not meet two different pickers
 * in one night.
 *
 * The names come from the session roster rather than deduplicated queue
 * strings, so it includes everyone who has joined, been picked, or been added
 * by name - not just people who have already queued something. "Someone else…"
 * swaps in a text field for the one-off case, which is also the only thing on
 * offer when the roster is empty.
 */

import React from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { SessionPerformer } from "@/types/SessionPerformer";

interface RosterPickerProps {
  /** The session's roster, seat order. */
  roster: SessionPerformer[];
  /** The name currently chosen - a roster name, or free text. */
  value: string;
  onChange: (name: string) => void;
  /**
   * Whether the free-text field is showing. Owned by the caller so that
   * "Someone else…" and the reset back to the grid survive re-renders from the
   * queue broadcasts arriving underneath.
   */
  showOther: boolean;
  onShowOtherChange: (showOther: boolean) => void;
  /** Ids to leave out - the handoff screen hides the person being passed over. */
  excludeIds?: number[];
  className?: string;
}

export const RosterPicker: React.FC<RosterPickerProps> = ({
  roster,
  value,
  onChange,
  showOther,
  onShowOtherChange,
  excludeIds = [],
  className = "",
}) => {
  const choices = roster.filter((p) => !excludeIds.includes(p.id));

  return (
    <div className={className}>
      {!showOther && choices.length > 0 && (
        <div className="flex flex-wrap justify-center gap-3">
          {choices.map((performer) => (
            <Button
              key={performer.id}
              variant={value === performer.name ? "primary" : "outline"}
              size="lg"
              onClick={() => onChange(performer.name)}
              className="rounded-full text-lg"
            >
              {performer.name}
            </Button>
          ))}
          <Button
            variant="ghost"
            size="lg"
            onClick={() => {
              onChange("");
              onShowOtherChange(true);
            }}
            className="rounded-full text-lg"
          >
            Someone else…
          </Button>
        </div>
      )}

      {showOther && (
        <div className="space-y-2">
          <Input
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder="Enter a name"
            maxLength={50}
            autoFocus
            className="h-14 text-center text-2xl"
          />
          {choices.length > 0 && (
            <Button
              variant="ghost"
              onClick={() => {
                onChange(choices[0]?.name ?? "");
                onShowOtherChange(false);
              }}
            >
              Pick from the roster instead
            </Button>
          )}
        </div>
      )}
    </div>
  );
};

export default RosterPicker;
