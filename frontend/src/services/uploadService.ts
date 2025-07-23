/**
 * Upload-related API services
 */
import { useMutation } from "@tanstack/react-query";
import { uploadFile } from "@/hooks/api/useApi";

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

/**
 * Hook for dismissing failed, completed, or cancelled jobs from the UI
 */
export function useDismissJob(
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
      const response = await fetch(`/api/jobs/${taskId}/dismiss`, {
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
