/**
 * Roster-related API hooks
 */
import { useApiMutation, useApiQuery } from "./useApi";
import type { UseQueryOptions } from "@tanstack/react-query";
import type { SessionPerformer } from "@/types/SessionPerformer";

type RosterQueryOptions = Omit<
  UseQueryOptions<
    SessionPerformer[],
    Error,
    SessionPerformer[],
    ["roster", string]
  >,
  "queryKey" | "queryFn"
>;

/**
 * Hook: Get the session's roster - everyone who has joined, been picked, or
 * been added by name, whether or not they have a device attached.
 */
export function useRoster(sessionCode?: string, options?: RosterQueryOptions) {
  return useApiQuery<SessionPerformer[], ["roster", string]>(
    ["roster", sessionCode || ""],
    `sessions/${sessionCode}/performers`,
    { enabled: Boolean(sessionCode), ...options },
  );
}

/**
 * Hook: Add a name to the roster without queueing anything - for pre-adding
 * someone who isn't touching a screen right now.
 */
export function useAddPerformer(sessionCode?: string) {
  return useApiMutation<SessionPerformer, { name: string }>(
    `sessions/${sessionCode}/performers`,
    "post",
  );
}
