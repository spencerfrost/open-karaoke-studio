/**
 * PhoneTopBar - the top bar: what's playing and who's singing it, on one
 * line, and Close.
 *
 * The page has no bottom nav (the faders need the height), so Close is the
 * way out: back to wherever the singer came from, or to the songbook when the
 * controls were the first page this tab opened.
 */

import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useQueue } from "@/hooks/api/useKaraokeQueue";
import { sessionWebSocketService } from "@/services/sessionWebSocketService";
import { useSessionStore } from "@/stores/sessionStore";

const PhoneTopBar: React.FC = () => {
  const navigate = useNavigate();
  const displayCode = useSessionStore((state) => state.displayCode);
  const { data: queue, refetch } = useQueue(displayCode ?? undefined);

  // The phone isn't otherwise watching the queue: refresh whenever it moves.
  useEffect(
    () => sessionWebSocketService.on("queue_updated", () => void refetch()),
    [refetch],
  );

  const close = () => {
    // React Router numbers its history entries; 0 is the first in this tab.
    const idx = (window.history.state as { idx?: number } | null)?.idx ?? 0;
    if (idx > 0) navigate(-1);
    else navigate("/", { replace: true });
  };

  const current = queue?.current;

  return (
    <div className="flex shrink-0 items-center gap-2 pl-1">
      <p className="min-w-0 flex-1 truncate text-base text-foreground-dim">
        {current ? (
          <>
            <span className="font-semibold text-foreground">
              {current.song.title}
            </span>
            {" · "}
            {current.singer}
          </>
        ) : (
          "Nothing playing yet"
        )}
      </p>
      <Button
        variant="ghost"
        onClick={close}
        className="h-10 shrink-0 gap-1 px-2.5 text-base font-semibold text-foreground-dim hover:text-foreground"
      >
        <X className="size-5" />
        Close
      </Button>
    </div>
  );
};

export default PhoneTopBar;
