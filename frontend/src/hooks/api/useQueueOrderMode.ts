/**
 * Switch a session between append (insert order) and rotation (strict
 * round-robin by lap) queue ordering. Session-owner only - see
 * docs/plans/archive/2026-08-29-roster-and-rotation.md.
 */
import { useApiMutation } from "./useApi";

export type QueueOrderMode = "append" | "rotation";

interface QueueOrderModeResponse {
  queue_order_mode: QueueOrderMode;
}

export function useSetQueueOrderMode(sessionId?: string) {
  return useApiMutation<QueueOrderModeResponse, { mode: QueueOrderMode }>(
    `sessions/${sessionId}/queue-order-mode`,
    "patch",
  );
}
