import { useState } from "react";
import { toast } from "sonner";
import {
  useCancelProcessing,
  useDismissJob,
} from "../services/uploadService";
import { useJobsWebSocket } from "@/hooks/api/useJobsWebSocket";
import { formatTaskId, countActiveJobs } from "../components/JobsQueue/JobsQueue.utils";
import { JobItem } from "../components/JobsQueue/JobsQueue.types";

export function useJobsQueue() {
  const [isOpen, setIsOpen] = useState(false);
  
  // Use WebSocket for real-time job updates
  const {
    jobs: processingItems = [],
    isConnected,
    error,
    refetch,
  } = useJobsWebSocket();

  // Use React Query for cancel mutation
  const cancelMutation = useCancelProcessing({
    onSuccess: (_, taskId) => {
      toast.success(`Job ${formatTaskId(taskId)} cancelled successfully.`);
      refetch();
    },
    onError: (err) => {
      console.error(err);
    },
  });

  // Use React Query for dismiss mutation
  const dismissMutation = useDismissJob({
    onSuccess: (_, taskId) => {
      toast.success(`Job ${formatTaskId(taskId)} dismissed successfully.`);
      refetch();
    },
    onError: (err) => {
      toast.error(`Failed to dismiss job: ${err.message}`);
      console.error(err);
    },
  });

  // Handle canceling a processing task
  const handleCancel = (taskId: string) => {
    toast.info(`Attempting to cancel job ${formatTaskId(taskId)}...`);
    cancelMutation.mutate(taskId);
  };

  // Handle dismissing a failed/completed task
  const handleDismiss = (taskId: string) => {
    toast.info(`Dismissing job ${formatTaskId(taskId)}...`);
    dismissMutation.mutate(taskId);
  };

  // Transform processing items to JobItem format
  const jobs: JobItem[] = processingItems.map(item => ({
    id: item.id,
    progress: item.progress,
    status: item.status,
    message: item.message,
    artist: item.artist,
    title: item.title,
  }));

  // Count active jobs
  const activeJobsCount = countActiveJobs(jobs);

  return {
    // State
    isOpen,
    setIsOpen,
    jobs,
    isConnected,
    error,
    activeJobsCount,
    
    // Actions
    handleCancel,
    handleDismiss,
    refetch,
  };
}