/**
 * Upload-related API services
 */
import { useMutation, useQuery } from "@tanstack/react-query";
import { uploadFile } from "@/hooks/useApi";
import { SongProcessingStatus, SongStatus } from "../types/Song";
import { jobsWebSocketService } from "./jobsWebSocketService";

/**
 * Hook: Upload and process an audio file
 */
type UploadAudioVariables = {
  file: File;
  metadata?: { title?: string; artist?: string };
};
type UploadAudioResponse = { id: string; status: string };
export function useUploadAndProcessAudio(
  options?: Omit<
    import("@tanstack/react-query").UseMutationOptions<
      UploadAudioResponse,
      Error,
      UploadAudioVariables,
      unknown
    >,
    "mutationFn"
  >
) {
  return useMutation<UploadAudioResponse, Error, UploadAudioVariables, unknown>(
    {
      mutationFn: async ({ file, metadata }) => {
        return uploadFile<UploadAudioResponse>("process", file, metadata);
      },
      ...options,
    }
  );
}

/**
 * Hook: Process a YouTube video
 */
type ProcessYouTubeVariables = {
  youtubeUrl: string;
  metadata?: { title?: string; artist?: string };
};
type ProcessYouTubeResponse = { id: string; status: string };
export function useProcessYouTubeVideo(
  options?: Omit<
    import("@tanstack/react-query").UseMutationOptions<
      ProcessYouTubeResponse,
      Error,
      ProcessYouTubeVariables,
      unknown
    >,
    "mutationFn"
  >
) {
  return useMutation<
    ProcessYouTubeResponse,
    Error,
    ProcessYouTubeVariables,
    unknown
  >({
    mutationFn: async ({ youtubeUrl, metadata }) => {
      const response = await fetch(`/api/process-youtube`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: youtubeUrl, ...metadata }),
      });
      if (!response.ok) {
        let errorMessage = `HTTP error! Status: ${response.status}`;
        try {
          const errorData: { message?: string } = await response.json();
          errorMessage = errorData?.message || errorMessage;
        } catch (jsonError) {
          console.error("Error parsing error response:", jsonError);
        }
        throw new Error(errorMessage);
      }
      return await response.json();
    },
    ...options,
  });
}

/**
 * Hook: Get all currently processing jobs (deprecated - use useJobsWebSocket instead)
 */
type BackendJob = {
  id: string;
  progress?: number;
  status: string;
  error?: string;
  notes?: string;
};

/**
 * Maps backend job status to frontend SongStatus
 */
function mapBackendStatus(backendStatus: string): SongStatus {
  switch (backendStatus) {
    case "pending":
      return "queued";
    case "processing":
      return "processing";
    case "completed":
      return "processed";
    case "failed":
    case "cancelled":
      return "error";
    default:
      return "error";
  }
}

/**
 * Hook: Cancel a processing task
 */

export function useCancelProcessing(
  options?: Omit<
    import("@tanstack/react-query").UseMutationOptions<
      { success: boolean },
      Error,
      string,
      unknown
    >,
    "mutationFn"
  >
) {
  return useMutation<{ success: boolean }, Error, string, unknown>({
    mutationFn: async (taskId: string) => {
      const response = await fetch(`/api/jobs/${taskId}/cancel`, {
        method: "POST",
      });
      if (!response.ok) {
        let errorMessage = `HTTP error! Status: ${response.status}`;
        try {
          const errorData: { message?: string } = await response.json();
          errorMessage = errorData?.message || errorMessage;
        } catch (jsonError) {
          console.error("Error parsing error response:", jsonError);
        }
        throw new Error(errorMessage);
      }
      return await response.json();
    },
    ...options,
  });
}
