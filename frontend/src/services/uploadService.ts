/**
 * Upload-related API services
 */
import { uploadFile, apiRequest } from "./api";
import { SongProcessingStatus, SongStatus } from "../types/Song";

/**
 * Upload and process an audio file
 */
export async function uploadAndProcessAudio(
  file: File,
  metadata?: { title?: string; artist?: string },
) {
  return uploadFile<{ id: string; status: string }>("/process", file, metadata);
}

/**
 * Process a YouTube video
 */
export async function processYouTubeVideo(
  youtubeUrl: string,
  metadata?: { title?: string; artist?: string },
) {
  return apiRequest<{ id: string; status: string }>("/process-youtube", {
    method: "POST",
    body: {
      url: youtubeUrl,
      ...metadata,
    },
  });
}

/**
 * Get all currently processing tasks
 */
export async function getProcessingQueue() {
  // Get jobs from the queue endpoint
  const response = await apiRequest<{ jobs: any[] }>("/queue/jobs");

  if (response.error) {
    return response;
  }

  if (response.data && response.data.jobs) {
    // Transform backend job format to frontend SongProcessingStatus format
    const processedData: SongProcessingStatus[] = response.data.jobs
      // Only include pending, processing, or failed jobs
      .filter((job) => ["pending", "processing", "failed"].includes(job.status))
      .map((job) => ({
        id: job.id,
        progress: job.progress || 0,
        status: mapBackendStatus(job.status),
        message: job.error || job.notes || undefined,
      }));

    return {
      data: processedData,
      error: null,
    };
  }

  return response;
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
 * Get the status of a processing task
 */
export async function getProcessingStatus(taskId: string) {
  const response = await apiRequest<any>(`/queue/job/${taskId}`);

  if (response.error) {
    return response;
  }

  if (response.data) {
    // Transform backend job format to frontend SongProcessingStatus format
    const processedData: SongProcessingStatus = {
      id: response.data.id,
      progress: response.data.progress || 0,
      status: mapBackendStatus(response.data.status),
      message: response.data.error || response.data.notes || undefined,
    };

    return {
      data: processedData,
      error: null,
    };
  }

  return response;
}

/**
 * Cancel a processing task
 */
export async function cancelProcessing(taskId: string) {
  return apiRequest<{ success: boolean }>(`/queue/job/${taskId}/cancel`, {
    method: "POST",
  });
}
