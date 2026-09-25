/**
 * QueueSingerDialog - "who's singing?" for queueing from the library.
 *
 * On a host's device the queue button used to credit the song to the host's own
 * display name, so every song added from the library landed under "admin". The
 * stage asks on its confirm screen; this asks the same question, with the same
 * RosterPicker, everywhere else a host device can queue from.
 */

import React, { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useRoster } from "@/hooks/api/useRoster";
import { useSessionStore } from "@/stores/sessionStore";
import type { Song } from "@/types/Song";
import type { SessionPerformer } from "@/types/SessionPerformer";
import RosterPicker from "@/features/stage/components/RosterPicker";

interface QueueSingerDialogProps {
  song: Song;
  isOpen: boolean;
  onClose: () => void;
  onQueue: (singerName: string) => void;
}

export const QueueSingerDialog: React.FC<QueueSingerDialogProps> = ({
  song,
  isOpen,
  onClose,
  onQueue,
}) => {
  const displayCode = useSessionStore((state) => state.displayCode);
  const rosterQuery = useRoster(displayCode ?? undefined, {
    enabled: isOpen && Boolean(displayCode),
  });

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent onClick={(e) => e.stopPropagation()}>
        <DialogHeader>
          <DialogTitle>Who's singing?</DialogTitle>
          <DialogDescription className="truncate">
            {song.title}
            {song.artist ? ` — ${song.artist}` : ""}
          </DialogDescription>
        </DialogHeader>

        {/* Keyed on the roster arriving so the default pick is made against
            real names rather than the empty list of the first render. */}
        {isOpen && !rosterQuery.isLoading && (
          <SingerForm
            key={rosterQuery.dataUpdatedAt}
            roster={rosterQuery.data ?? []}
            onCancel={onClose}
            onSubmit={(name) => {
              onQueue(name);
              toast.success(`Added "${song.title}" for ${name}`);
              onClose();
            }}
          />
        )}
      </DialogContent>
    </Dialog>
  );
};

const SingerForm: React.FC<{
  roster: SessionPerformer[];
  onCancel: () => void;
  onSubmit: (name: string) => void;
}> = ({ roster, onCancel, onSubmit }) => {
  const [singer, setSinger] = useState(roster[0]?.name ?? "");
  const [showOther, setShowOther] = useState(roster.length === 0);
  const trimmed = singer.trim();

  return (
    // Not a <form>: RosterPicker's name buttons have no type, so inside one
    // every tap on a name would submit.
    <div className="space-y-6">
      <RosterPicker
        roster={roster}
        value={singer}
        onChange={setSinger}
        showOther={showOther}
        onShowOtherChange={setShowOther}
      />
      <DialogFooter>
        <Button variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button disabled={!trimmed} onClick={() => onSubmit(trimmed)}>
          Add to queue
        </Button>
      </DialogFooter>
    </div>
  );
};

export default QueueSingerDialog;
