/**
 * Turn-related API hooks - what the handoff screen can do to a turn.
 *
 * Every one of them sends `expected_performer_id`: the turn the screen was
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

export interface ClaimTurnVariables extends ExpectedTurn {
  /** An existing roster entry... */
  performerId?: number;
  /** ...or a new name from the picker's "Someone else…" field. */
  name?: string;
}

/** Raised for a 409 so callers can tell "someone beat me to it" from a real failure. */
export class TurnMovedOnError extends Error {
  constructor() {
    super("The turn has already moved on");
    this.name = "TurnMovedOnError";
  }
}

async function postTurn(
  url: string,
  body: Record<string, unknown>,
): Promise<SessionPerformer> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(body),
  });
  if (response.status === 409) throw new TurnMovedOnError();
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return (await response.json()) as SessionPerformer;
}

/** Hook: hand the turn to someone else - the screen's "That's not me". */
export function useClaimTurn(sessionCode?: string) {
  return useMutation<SessionPerformer, Error, ClaimTurnVariables>({
    mutationFn: ({ expectedPerformerId, performerId, name }) =>
      postTurn(`/api/sessions/${sessionCode}/turn/claim`, {
        expected_performer_id: expectedPerformerId,
        performer_id: performerId,
        name,
      }),
  });
}

/**
 * Hook: step someone out of the rotation - the screen's "Skip me for now".
 *
 * Deliberate and self-service - the only way a seat leaves the rotation. The
 * seat comes back the moment they queue something, claim a turn, or join again.
 */
export function useDeactivatePerformer(sessionCode?: string) {
  return useMutation<SessionPerformer, Error, number>({
    mutationFn: (performerId) =>
      postTurn(
        `/api/sessions/${sessionCode}/performers/${performerId}/deactivate`,
        {},
      ),
  });
}
