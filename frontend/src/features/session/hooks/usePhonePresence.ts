/**
 * The phone's half of "your turn on the phone".
 *
 * Two jobs, both app-wide so they run on whatever page the device is on:
 *
 * 1. **Report presence.** Every session device tells the server whether its
 *    page is on screen (Page Visibility API) and whether it is the controls.
 *    The stage uses this to ask a singer to take their phone out.
 * 2. **Open the controls when this device's song starts.** The queue's
 *    `current` item names the seat whose song is playing; the server tells this
 *    device which seat it is. When they match, the phone goes to `/controls` -
 *    once per song, so it never drags someone back after they have left.
 *
 * Note it is `current`, not `turn`, that decides: the moment a song starts the
 * turn pointer moves on to whoever is next.
 */

import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { createLogger } from "@/lib/logger";
import { sessionWebSocketService } from "@/services/sessionWebSocketService";
import { useSessionStore } from "@/stores/sessionStore";
import { shouldOpenControls, usePresenceStore } from "@/stores/presenceStore";

const logger = createLogger("hook:phone-presence");

const CONTROLS_PATH = "/controls";

type CurrentItem = { id: string | number; performerId?: number | null };

function isOnScreen(): boolean {
  return document.visibilityState === "visible";
}

export function usePhonePresence(): void {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const sessionId = useSessionStore((s) => s.sessionId);
  const isStageDevice = useSessionStore((s) => s.isStageDevice);
  const onControls = pathname === CONTROLS_PATH;

  // --- 1. Presence ---------------------------------------------------------
  useEffect(() => {
    if (!sessionId) return;

    const report = () =>
      sessionWebSocketService.setPresence({
        visible: isOnScreen(),
        onControls,
      });
    report();

    const handleVisibility = () => {
      report();
      // Coming back to the page: the socket may have been reconnected while
      // hidden, and a song that started meanwhile has to be noticed now.
      if (isOnScreen() && !isStageDevice) {
        sessionWebSocketService.requestQueueUpdate();
      }
    };
    document.addEventListener("visibilitychange", handleVisibility);
    return () =>
      document.removeEventListener("visibilitychange", handleVisibility);
  }, [sessionId, isStageDevice, onControls]);

  // --- 2. The song that is playing -------------------------------------------
  // Phones don't otherwise listen to the queue, so ask for it on every (re)join
  // of the queue room and keep only `current`. The stage page fetches its own.
  const [current, setCurrent] = useState<CurrentItem | null>(null);
  useEffect(() => {
    if (!sessionId || isStageDevice) return;

    const offJoined = sessionWebSocketService.on("queue_joined", () => {
      sessionWebSocketService.requestQueueUpdate();
    });
    const offUpdated = sessionWebSocketService.on("queue_updated", (data) => {
      // A bare trigger carries no state; only a full payload says what is on.
      if (!("current" in data)) return;
      setCurrent(data.current ?? null);
    });
    if (sessionWebSocketService.isConnectionActive()) {
      sessionWebSocketService.requestQueueUpdate();
    }
    return () => {
      offJoined();
      offUpdated();
      setCurrent(null);
    };
  }, [sessionId, isStageDevice]);

  const myPerformerId = usePresenceStore((s) => s.myPerformerId);
  const autoOpenedItemId = usePresenceStore((s) => s.autoOpenedItemId);
  const markAutoOpened = usePresenceStore((s) => s.markAutoOpened);

  useEffect(() => {
    if (isStageDevice || !current) return;
    if (!shouldOpenControls({ current, myPerformerId, autoOpenedItemId })) {
      return;
    }
    markAutoOpened(String(current.id));
    if (!onControls) {
      logger.info("This device's song started - opening the controls");
      navigate(CONTROLS_PATH);
    }
  }, [
    current,
    myPerformerId,
    autoOpenedItemId,
    markAutoOpened,
    isStageDevice,
    onControls,
    navigate,
  ]);
}
