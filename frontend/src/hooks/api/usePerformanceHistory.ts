import { useApiQuery } from "./useApi";
import { createLogger } from "@/lib/logger";

const logger = createLogger("hook:performanceHistory");

const QUERY_KEYS = {
  performanceHistory: (limit: number, offset: number) =>
    ["performance-history", limit, offset] as const,
};

export interface PerformanceHistoryItem {
  id: number;
  song_id: string | null;
  song_title: string | null;
  artist: string | null;
  singer_name: string;
  session_code: string | null;
  performed_at: string;
}

export interface PerformanceHistoryResponse {
  items: PerformanceHistoryItem[];
  total: number;
  limit: number;
  offset: number;
}

export function usePerformanceHistory(limit = 50, offset = 0) {
  logger.debug("Fetching performance history", { limit, offset });
  return useApiQuery<PerformanceHistoryResponse, readonly [string, number, number]>(
    QUERY_KEYS.performanceHistory(limit, offset),
    `performance-history?limit=${limit}&offset=${offset}`,
  );
}
