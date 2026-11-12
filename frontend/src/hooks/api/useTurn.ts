/**
 * Turn-related API hooks - what the handoff screen can do to a turn.
 *
 * Rotation is a fixed circle of seats with a pointer to whose turn it is.
 * These move the pointer or change who is in the circle.
 *
 * The turn-changing ones send `expected_performer_id`: the turn the screen was
 * rendering when someone tapped. The server compares it against the turn it
 * computes and answers 409 if it has already moved on, so a phone and the TV
 * acting at the same moment settle on one outcome instead of both landing.
 */
import { useMutation } from "@tanstack/react-query";
import { getAuthHeaders } from "./useApi";
import type { SessionPerformer } from "@/types/SessionPerformer";

/** The turn the caller believed it was acting on. */
interface ExpectedTurn {
  expectedPerformerId: number | null;
}

export interface InsertPerformerVariables extends ExpectedTurn {
  name: string;
}

export interface RemovePerformerVariables extends ExpectedTurn {
  performerId: number;
}

export interface RestorePerformerVariables {
  performerId: number;
  /** `holderId` from the remove - proves the turn hasn't moved since. */
  expectedHolderId: number | null;
}

/** A removed performer, plus whose turn it is now - what the undo sends back. */
export interface RemovedPerformer extends SessionPerformer {
  holder_id: number | null;
}

/** Raised for a 409 so callers can tell "someone beat me to it" from a real failure. */
export class TurnMovedOnError extends Error {
  constructor() {
    super("The turn has already moved on");
    this.name = "TurnMovedOnError";
  }
}

async function postTurn<T = SessionPerformer>(
  url: string,
  body: Record<string, unknown>,
): Promise<T> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(body),
  });
  if (response.status === 409) throw new TurnMovedOnError();
  if (!response.ok) {
    // The server's detail is written for people ("Dan is already in the
    // rotation"), so pass it through.
    const detail = await response
      .json()
      .then((json: { detail?: unknown }) => json.detail)
      .catch(() => undefined);
    throw new Error(
      typeof detail === "string"
        ? detail
        : `Request failed with status ${response.status}`,
    );
  }
  return (await response.json()) as T;
}

/**
 * Hook: "Skip my turn". The turn moves to the next seat; their songs stay
 * queued, each one a lap later.
 */
export function useSkipTurn(sessionCode?: string) {
  return useMutation<SessionPerformer, Error, ExpectedTurn>({
    mutationFn: ({ expectedPerformerId }) =>
      postTurn(`/api/sessions/${sessionCode}/turn/skip`, {
        expected_performer_id: expectedPerformerId,
      }),
  });
}

/**
 * Hook: "Add performer". Seats a name at the turn - they're up now, whoever
 * was up goes next. A removed person's name brings them back the same way.
 */
export function useInsertPerformer(sessionCode?: string) {
  return useMutation<SessionPerformer, Error, InsertPerformerVariables>({
    mutationFn: ({ expectedPerformerId, name }) =>
      postTurn(`/api/sessions/${sessionCode}/turn/insert`, {
        expected_performer_id: expectedPerformerId,
        name,
      }),
  });
}

/**
 * Hook: "Remove from rotation". Out for the night; their songs are hidden,
 * not deleted, and their seat is kept for the undo.
 */
export function useRemovePerformer(sessionCode?: string) {
  return useMutation<RemovedPerformer, Error, RemovePerformerVariables>({
    mutationFn: ({ expectedPerformerId, performerId }) =>
      postTurn<RemovedPerformer>(
        `/api/sessions/${sessionCode}/performers/${performerId}/remove`,
        { expected_performer_id: expectedPerformerId },
      ),
  });
}

/**
 * Hook: undo a remove. Same seat, and their turn back if nothing has happened
 * since - otherwise they just rejoin their seat.
 */
export function useRestorePerformer(sessionCode?: string) {
  return useMutation<SessionPerformer, Error, RestorePerformerVariables>({
    mutationFn: ({ performerId, expectedHolderId }) =>
      postTurn(
        `/api/sessions/${sessionCode}/performers/${performerId}/restore`,
        { expected_holder_id: expectedHolderId },
      ),
  });
}
