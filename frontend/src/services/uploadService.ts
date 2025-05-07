/**
 * Upload-related API services
 */
import { useMutation, useQuery } from "@tanstack/react-query";
import { uploadFile } from "@/hooks/useApi";
import { SongProcessingStatus, SongStatus } from "../types/Song";

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
 * Hook: Get all currently processing tasks
 */
type BackendJob = {
  id: string;
  progress?: number;
  status: string;
  error?: string;
  notes?: string;
};

export function useProcessingQueue(
  options?: Omit<
    import("@tanstack/react-query").UseQueryOptions<
      SongProcessingStatus[],
      Error,
      SongProcessingStatus[],
      ["processing-queue"]
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery<
    SongProcessingStatus[],
    Error,
    SongProcessingStatus[],
    ["processing-queue"]
  >({
    queryKey: ["processing-queue"],
    queryFn: async () => {
      const response = await fetch(`/api/queue/jobs`);
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
      const data: { jobs?: BackendJob[] } = await response.json();
      if (data && data.jobs) {
        return data.jobs
          .filter((job) =>
            ["pending", "processing", "failed"].includes(job.status)
          )
          .map((job) => ({
            id: job.id,
            progress: job.progress || 0,
            status: mapBackendStatus(job.status),
            message: job.error || job.notes || undefined,
          })) as SongProcessingStatus[];
      }
      return [];
    },
    ...options,
  });
}

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
 * Hook: Get the status of a processing task
 */

export function useProcessingStatus(
  taskId: string,
  options?: Omit<
    import("@tanstack/react-query").UseQueryOptions<
      SongProcessingStatus,
      Error,
      SongProcessingStatus,
      ["processing-status", string]
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery<
    SongProcessingStatus,
    Error,
    SongProcessingStatus,
    ["processing-status", string]
  >({
    queryKey: ["processing-status", taskId],
    queryFn: async () => {
      const response = await fetch(`/api/queue/job/${taskId}`);
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
      const data: BackendJob = await response.json();
      return {
        id: data.id,
        progress: data.progress || 0,
        status: mapBackendStatus(data.status),
        message: data.error || data.notes || undefined,
      } as SongProcessingStatus;
    },
    ...options,
  });
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
      const response = await fetch(`/api/queue/job/${taskId}/cancel`, {
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
