import { JobItem, JobStatusInfo } from "./JobsQueue.types";

/**
 * Get status label and badge variant for a job
 */
export function getJobStatusInfo(status: string): JobStatusInfo {
  switch (status?.toLowerCase()) {
    case "processing":
      return { label: "Processing", variant: "default" };
    case "error":
      return { label: "Failed", variant: "destructive" };
    case "processed":
      return { label: "Completed", variant: "secondary" };
    case "queued":
    default:
      return { label: "Queued", variant: "secondary" };
  }
}

/**
 * Count active jobs (processing, queued, or error)
 */
export function countActiveJobs(jobs: JobItem[]): number {
  return jobs.filter(
    (item) => 
      item.status === "processing" || 
      item.status === "queued" || 
      item.status === "error"
  ).length;
}

/**
 * Format task ID for display (first 8 characters)
 */
export function formatTaskId(taskId: string): string {
  return taskId.substring(0, 8);
}