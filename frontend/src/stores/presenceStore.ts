/**
 * Presence - whose phone is open, and which seat this device is.
 *
 * Filled entirely from the session socket:
 * - `session_connected.presence` and `presence_updated` say, per roster seat
 *   with a phone linked, whether that phone is connected, on screen and on the
 *   controls. The stage reads this for its "open your phone" prompt.
 * - `presence_acknowledged` answers this device's own report with the seat it
 *   is linked to. The phone reads this to know when the song starting is its own.
 *
 * In memory only. Presence describes live sockets, so a reload should start
 * from what the server says rather than from what this tab last saw.
 */

import { create } from "zustand";
import { sessionWebSocketService } from "@/services/sessionWebSocketService";
import type { PerformerPresence } from "@/types/Presence";

interface PresenceState {
  /** The session these readings belong to. */
  sessionId: string | null;
  /** By performer id. Seats without a linked phone are absent. */
  performers: Record<number, PerformerPresence>;
  /** The roster seat this device is linked to; null for the stage or a nameless device. */
  myPerformerId: number | null;
  /**
   * The queue item whose start already sent this phone to `/controls`. Guards
   * against doing it again on every later broadcast during the same song.
   */
  autoOpenedItemId: string | null;
  /** When it did, in ms since epoch. A tour can wait on this changing. */
  autoOpenedAt: number | null;

  markAutoOpened: (itemId: string) => void;
  reset: () => void;
}

const initialState = {
  sessionId: null,
  performers: {},
  myPerformerId: null,
  autoOpenedItemId: null,
  autoOpenedAt: null,
} satisfies Partial<PresenceState>;

function byPerformer(
  list: PerformerPresence[] | undefined,
): Record<number, PerformerPresence> {
  const map: Record<number, PerformerPresence> = {};
  for (const entry of list ?? []) map[entry.performerId] = entry;
  return map;
}

export const usePresenceStore = create<PresenceState>()((set) => ({
  ...initialState,
  markAutoOpened: (itemId) =>
    set({ autoOpenedItemId: itemId, autoOpenedAt: Date.now() }),
  reset: () => set(initialState),
}));

/**
 * Should this phone open its controls for the song that is playing now?
 *
 * Only for a song that is this device's seat's, and only once per song: the
 * guard is the queue item id, so pauses, seeks and unrelated queue edits during
 * the song never send someone back after they have walked away. A song already
 * playing when the phone comes back counts as starting for it - that is the
 * "open your phone" prompt's other half.
 */
export function shouldOpenControls(args: {
  current: { id: string | number; performerId?: number | null } | null;
  myPerformerId: number | null;
  autoOpenedItemId: string | null;
}): boolean {
  const { current, myPerformerId, autoOpenedItemId } = args;
  if (!current || myPerformerId === null) return false;
  if (current.performerId == null || current.performerId !== myPerformerId) {
    return false;
  }
  return String(current.id) !== autoOpenedItemId;
}

/**
 * Should the stage ask this singer to take their phone out?
 *
 * Only when the singer has a phone linked at all, and it is closed, locked or
 * in the background. A phone that is open but on another page needs no prompt:
 * it sees its turn and opens the controls itself.
 */
export function needsPhoneOpened(
  presence: PerformerPresence | undefined,
): boolean {
  if (!presence) return false;
  return !presence.connected || !presence.visible;
}

// Registered once at module scope against the singleton socket, like the
// session store's own listeners.
sessionWebSocketService.on("session_connected", (data) => {
  const { sessionId } = usePresenceStore.getState();
  // A different session means a different seat; a reconnect to the same one
  // keeps what it knew until the next acknowledgement corrects it.
  if (sessionId !== data.session_id) {
    usePresenceStore.setState({ ...initialState, sessionId: data.session_id });
  }
  usePresenceStore.setState({ performers: byPerformer(data.presence) });
});

sessionWebSocketService.on("presence_updated", (data) => {
  usePresenceStore.setState({ performers: byPerformer(data.performers) });
});

sessionWebSocketService.on("presence_acknowledged", (data) => {
  usePresenceStore.setState({ myPerformerId: data.performer_id ?? null });
});

sessionWebSocketService.on("session_ended", () => {
  usePresenceStore.getState().reset();
});
