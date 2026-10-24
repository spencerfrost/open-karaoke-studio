import { useApiQuery } from "@/hooks/api/useApi";

interface DemoStatusResponse {
  /** Any demo pool account is seeded on this server. */
  enabled: boolean;
}

/** Whether this server offers the live demo ("Try it live"). */
export function useDemoStatus() {
  const query = useApiQuery<DemoStatusResponse>(["demo", "status"], "demo", {
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
  return { enabled: query.data?.enabled ?? false };
}
