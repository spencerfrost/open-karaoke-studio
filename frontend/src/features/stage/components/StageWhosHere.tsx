/**
 * StageWhosHere - the join QR code in the song select screen's corner, and the
 * "Who's here" panel it opens.
 *
 * The panel answers what a guest wants to know right after scanning: did it
 * work, am I in, when do I sing? So it lists everyone in the rotation in turn
 * order, with where they stand (singing, up next, songs waiting, no song yet)
 * and whether their phone is open. Under that, the way in for anyone whose
 * camera won't read the code: the address to type and the join code, and on a
 * computer "Open a phone view", as on the performance screen.
 *
 * It opens on a click, not a hover. The mouse on the mic stand drifts across
 * this corner all night, and a panel that opened whenever it did would cover
 * the wheel for no one.
 *
 * Nothing in it is a host control. Anyone at the TV can open it, so leaving
 * the session and the queue settings live elsewhere (see RotationModeCard).
 * The server connection is only mentioned when it has been lost.
 */

import React, { useEffect, useMemo, useState } from "react";
import { WifiOff } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Item,
  ItemContent,
  ItemDescription,
  ItemGroup,
  ItemTitle,
} from "@/components/ui/item";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Separator } from "@/components/ui/separator";
import { QRCodeDisplay } from "@/features/queue";
import { useRoster } from "@/hooks/api/useRoster";
import { useAccess } from "@/hooks/useAccess";
import { openPhoneViewOrWarn } from "@/lib/guestWindow";
import { cn } from "@/lib/utils";
import { usePresenceStore } from "@/stores/presenceStore";
import { useSessionStore } from "@/stores/sessionStore";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { useStageQueue } from "../StageShellContext";
import { statusLabel, whosHere, type WhosHereRow } from "../whosHere";

interface StageWhosHereProps {
  className?: string; // Applied to outermost wrapper
}

const StageWhosHere: React.FC<StageWhosHereProps> = ({ className = "" }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const fsContainer = useFullscreenElement();

  const displayCode = useSessionStore((s) => s.displayCode);
  const { inSession, isStageDevice } = useAccess();
  const connected = useKaraokePlayerStore((s) => s.connected);
  const presence = usePresenceStore((s) => s.performers);
  const queue = useStageQueue();
  const rosterQuery = useRoster(displayCode || undefined);

  const rows = useMemo(
    () =>
      whosHere({
        roster: rosterQuery.data ?? [],
        current: queue?.current ?? null,
        upcoming: queue?.upcoming ?? [],
        turn: queue?.turn ?? null,
        presence,
      }),
    [rosterQuery.data, queue, presence],
  );

  // Only the host device shows the code to share.
  if (!inSession || !isStageDevice || !displayCode) return null;

  const joinUrl = `${window.location.origin}/join/${displayCode}`;

  if (isCollapsed) {
    return (
      <div className={className}>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIsCollapsed(false)}
          className="rounded-full bg-card/80"
        >
          Show join code
        </Button>
      </div>
    );
  }

  return (
    <div data-tour="join-code" className={className}>
      <Popover open={isOpen} onOpenChange={setIsOpen}>
        <PopoverTrigger asChild>
          <button
            type="button"
            aria-label={`Join code ${displayCode}. Show who's here`}
            className="cursor-pointer rounded-lg focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
          >
            <QRCodeDisplay value={joinUrl} size={100} />
          </button>
        </PopoverTrigger>
        <PopoverContent
          className="w-[22rem] p-0"
          side="top"
          align="end"
          container={fsContainer}
        >
          <div className="space-y-3 p-4">
            <div className="flex items-baseline justify-between gap-2">
              <h4 className="text-base font-semibold">
                Who's here
                {rows.length > 0 && (
                  <span className="ml-1.5 font-normal text-muted-foreground">
                    ({rows.length})
                  </span>
                )}
              </h4>
              <Button
                variant="link"
                size="sm"
                className="h-auto p-0 text-muted-foreground"
                onClick={() => {
                  setIsOpen(false);
                  setIsCollapsed(true);
                }}
              >
                Hide the code
              </Button>
            </div>

            {!connected && (
              <Alert variant="destructive">
                <WifiOff />
                <AlertTitle>Lost connection to the server</AlertTitle>
                <AlertDescription>
                  Trying again. New songs and names show up once it's back.
                </AlertDescription>
              </Alert>
            )}

            {rows.length > 0 ? (
              <ItemGroup className="-mx-2 max-h-[18rem] overflow-y-auto">
                {rows.map((row) => (
                  <SingerRow key={row.id} row={row} />
                ))}
              </ItemGroup>
            ) : (
              <p className="text-sm text-muted-foreground">
                Nobody has joined yet. Scan the code to add your name.
              </p>
            )}
          </div>

          <Separator />

          <div className="space-y-2 p-4 text-sm">
            <p className="text-muted-foreground">
              Camera won't scan? On your phone, go to
            </p>
            <p className="font-mono text-base break-all">
              {window.location.host}/join
            </p>
            <p className="flex items-baseline gap-2 text-muted-foreground">
              and enter
              <span className="font-accent text-2xl leading-none text-accent">
                {displayCode}
              </span>
            </p>
            <div className="hidden pt-1 pointer-fine:block">
              <Button
                variant="link"
                size="sm"
                onClick={() => openPhoneViewOrWarn(displayCode)}
                className="h-auto p-0"
              >
                No phone? Open a phone view
              </Button>
            </div>
          </div>
        </PopoverContent>
      </Popover>
    </div>
  );
};

const SingerRow: React.FC<{ row: WhosHereRow }> = ({ row }) => (
  <Item
    role="listitem"
    size="sm"
    className={cn("px-2 py-1.5", row.status === "singing" && "bg-muted/50")}
  >
    <ItemContent className="gap-0">
      <ItemTitle className="text-base">{row.name}</ItemTitle>
      <ItemDescription
        className={cn(row.status === "up_next" && "text-foreground")}
      >
        {statusLabel(row)}
      </ItemDescription>
    </ItemContent>
    {row.phone && (
      <span
        className={cn(
          "text-xs",
          row.phone === "open"
            ? "text-success-strong"
            : "text-muted-foreground",
        )}
      >
        {row.phone === "open" ? "Phone open" : "Phone closed"}
      </span>
    )}
  </Item>
);

/**
 * The element in fullscreen, if any. The popover has to portal into it: a
 * portal to <body> is drawn behind a fullscreen element and never seen.
 */
function useFullscreenElement(): HTMLElement | null {
  const [element, setElement] = useState<HTMLElement | null>(
    () => (document.fullscreenElement as HTMLElement) ?? null,
  );
  useEffect(() => {
    const update = () =>
      setElement((document.fullscreenElement as HTMLElement) ?? null);
    document.addEventListener("fullscreenchange", update);
    document.addEventListener("webkitfullscreenchange", update);
    return () => {
      document.removeEventListener("fullscreenchange", update);
      document.removeEventListener("webkitfullscreenchange", update);
    };
  }, []);
  return element;
}

export default StageWhosHere;
