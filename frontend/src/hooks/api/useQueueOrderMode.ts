/**
 * Switch a session between append (insert order) and rotation (strict
 * round-robin over the circle of performers) queue ordering. Session-owner only.
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
