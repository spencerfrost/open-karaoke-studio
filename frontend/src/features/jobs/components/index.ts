// Main component export
export { default } from "./JobsQueue";

// Export individual components for potential reuse
export { default as JobsQueueTrigger } from "./JobsQueueTrigger";
export { default as JobsQueueDrawer } from "./JobsQueueDrawer";
export { default as JobItemComponent } from "./JobItem";
export { default as ConnectionStatus } from "./ConnectionStatus";
export { default as EmptyState } from "./EmptyState";

// Export custom hook
export { useJobsQueue } from "../../hooks/useJobsQueue";

// Export types
export type {
  JobItem as JobItemType,
  JobStatusInfo,
  JobsQueueTriggerProps,
  JobsQueueDrawerProps,
  JobItemProps,
  ConnectionStatusProps,
  EmptyStateProps,
} from "./JobsQueue.types";

// Export utilities
export {
  getJobStatusInfo,
  countActiveJobs,
  formatTaskId,
} from "./JobsQueue.utils";
