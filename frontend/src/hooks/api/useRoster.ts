/**
 * Roster-related API hooks
 */
import { useEffect } from "react";
import { useQueryClient, type UseQueryOptions } from "@tanstack/react-query";
import { sessionWebSocketService } from "@/services/sessionWebSocketService";
import { useApiMutation, useApiQuery } from "./useApi";
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
  const queryClient = useQueryClient();

  // The server broadcasts every change to who is in the rotation - a join, an
  // "Add performer", a remove and its undo. Without this, a screen keeps the
  // roster it loaded and, for example, the confirm screen can't default to
  // someone added at the TV a moment ago.
  useEffect(() => {
    if (!sessionCode) return;
    return sessionWebSocketService.on("roster_updated", () => {
      void queryClient.invalidateQueries({
        queryKey: ["roster", sessionCode],
      });
    });
  }, [queryClient, sessionCode]);

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
