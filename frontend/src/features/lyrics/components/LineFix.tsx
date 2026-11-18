/**
 * Fixing a line of lyrics on the stage: the "Fix this line" button shown when
 * the line is pointed at, and the editor that opens in its place.
 *
 * Playback keeps going while the editor is open. Enter saves, Cancel (or
 * Escape) closes it. The fix replaces only this line and is kept for good;
 * the line's words are timed again on their own (useLyricsLineFixes).
 */

import React, { useState } from "react";
import { Pencil } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useSaveLineFix } from "@/hooks/api/useLyricsLineFixes";
import { createLogger } from "@/lib/logger";
import { useLineFixStore, type FixableLine } from "@/stores/useLineFixStore";

const logger = createLogger("component:LineFix");

/** Same limit as the server's: anything longer isn't one line. */
const MAX_LINE_LENGTH = 300;

interface FixLineButtonProps {
  line: FixableLine;
}

/** Shown beside a line while it's pointed at (or focused). */
export const FixLineButton: React.FC<FixLineButtonProps> = ({ line }) => {
  const startEditing = useLineFixStore((s) => s.startEditing);
  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      // At the row's right edge, so the centred line doesn't move when it
      // shows. Plain :hover, not group-hover: Tailwind's hover variant waits
      // for (hover: hover), and the Shield reports no pointer at all even
      // with a mouse plugged in. While hidden it takes no clicks, so a tap on
      // the line's right edge still seeks instead of opening the editor.
      className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 whitespace-nowrap text-base font-normal opacity-0 transition-opacity group-[:hover]:pointer-events-auto group-[:hover]:opacity-100 focus-visible:pointer-events-auto focus-visible:opacity-100 [text-shadow:none]"
      onClick={(e) => {
        e.stopPropagation();
        startEditing(line);
      }}
    >
      <Pencil aria-hidden="true" />
      Fix this line
    </Button>
  );
};

interface LineFixEditorProps {
  line: FixableLine;
}

/** The line's words in a text box, in place of the line. */
export const LineFixEditor: React.FC<LineFixEditorProps> = ({ line }) => {
  const songId = useLineFixStore((s) => s.songId);
  const stopEditing = useLineFixStore((s) => s.stopEditing);
  const [text, setText] = useState(line.content);
  const saveFix = useSaveLineFix();

  const save = () => {
    if (!songId) return;
    const trimmed = text.trim();
    if (!trimmed || trimmed === line.content.trim()) {
      stopEditing();
      return;
    }
    saveFix.mutate(
      {
        songId,
        lineStart: line.timestamp / 1000,
        oldText: line.content,
        newText: trimmed,
      },
      {
        onSuccess: () => {
          toast.success("Line fixed. It stays fixed next time too.");
          stopEditing();
        },
        onError: (error) => {
          logger.warn("Saving a line fix failed", error);
          toast.error(`Couldn't fix the line: ${error.message}`);
        },
      },
    );
  };

  return (
    <form
      className="flex w-full flex-col items-center gap-3 [text-shadow:none]"
      onSubmit={(e) => {
        e.preventDefault();
        save();
      }}
      // Keys typed here are words, not stage shortcuts.
      onKeyDown={(e) => {
        e.stopPropagation();
        if (e.key === "Escape") {
          e.preventDefault();
          stopEditing();
        }
      }}
      onClick={(e) => e.stopPropagation()}
    >
      <Input
        autoFocus
        aria-label="The words of this line"
        value={text}
        maxLength={MAX_LINE_LENGTH}
        disabled={saveFix.isPending}
        onChange={(e) => setText(e.target.value)}
        onFocus={(e) => e.currentTarget.select()}
        className="h-auto w-[min(56rem,100%)] py-3 text-center text-3xl font-normal md:text-3xl"
      />
      <div className="flex items-center gap-3 text-base font-normal">
        <Button type="submit" variant="primary" disabled={saveFix.isPending}>
          {saveFix.isPending ? "Saving…" : "Save"}
        </Button>
        <Button
          type="button"
          variant="ghost"
          disabled={saveFix.isPending}
          onClick={stopEditing}
        >
          Cancel
        </Button>
        <span className="text-muted-foreground">Enter saves</span>
      </div>
    </form>
  );
};
