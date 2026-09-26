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
import { useQueue } from "@/hooks/api/useKaraokeQueue";
import { useRoster } from "@/hooks/api/useRoster";
import { useSessionStore } from "@/stores/sessionStore";
import type { Song } from "@/types/Song";
import type { SessionPerformer } from "@/types/SessionPerformer";
import type { SessionTurn } from "@/types/KaraokeQueue";
import RosterPicker from "@/features/stage/components/RosterPicker";
import { useDefaultSinger } from "@/features/stage/hooks/useDefaultSinger";

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
  // Only for the turn, so the pick starts on whoever is up.
  const queueQuery = useQueue(displayCode ?? undefined, { enabled: isOpen });

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

        {/* Held back until the roster and turn load so the picker opens on
            the right name instead of jumping to it. Anything that changes
            after that moves the default through useDefaultSinger. */}
        {isOpen && !rosterQuery.isLoading && !queueQuery.isLoading && (
          <SingerForm
            roster={rosterQuery.data ?? []}
            turn={queueQuery.data?.turn}
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
  turn: SessionTurn | undefined;
  onCancel: () => void;
  onSubmit: (name: string) => void;
}> = ({ roster, turn, onCancel, onSubmit }) => {
  const [singer, setSinger] = useDefaultSinger(roster, turn);
  const [otherToggled, setShowOther] = useState<boolean | null>(null);
  const showOther = otherToggled ?? roster.length === 0;
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
