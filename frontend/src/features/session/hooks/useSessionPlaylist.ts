import { useApiQuery } from "@/hooks/api/useApi";
import type { SessionPlaylistStatus } from "@/services/api";

interface UseSessionPlaylistOptions {
  sessionId: string;
  enabled: boolean;
}

export function useSessionPlaylist({
  sessionId,
  enabled,
}: UseSessionPlaylistOptions) {
  return useApiQuery<SessionPlaylistStatus, readonly [string, string]>(
    ["session-playlist", sessionId],
    `sessions/${sessionId}/playlist`,
    {
      enabled,
      refetchInterval: (query) => {
        const status = query.state.data?.status;
        return status === "pending" || status === "processing" ? 3000 : false;
      },
      retry: false,
    },
  );
}
