import { useState } from "react";
import { toast } from "sonner";
import { useCancelProcessing, useDismissJob } from "@/services/uploadService";
import { useJobsWebSocket } from "@/hooks/api/useJobsWebSocket";
import { countActiveJobs } from "../components/JobsQueue.utils";
import { JobItem } from "../types/JobsQueue.types";

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
      refetch();
    },
    onError: (err) => {
      toast.error(`Failed to cancel job: ${err.message}`);
      console.error(err);
    },
  });

  // Use React Query for dismiss mutation
  const dismissMutation = useDismissJob({
    onSuccess: (_, taskId) => {
      refetch();
    },
    onError: (err) => {
      toast.error(`Failed to dismiss job: ${err.message}`);
      console.error(err);
    },
  });

  // Handle canceling a processing task
  const handleCancel = (taskId: string) => {
    if (!cancelMutation.isPending) {
      cancelMutation.mutate(taskId);
    }
  };

  // Handle dismissing a failed/completed task
  const handleDismiss = (taskId: string) => {
    if (!dismissMutation.isPending) {
      dismissMutation.mutate(taskId);
    }
  };

  // Transform processing items to JobItem format
  const jobs: JobItem[] = processingItems.map((item) => ({
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
    isCancelLoading: cancelMutation.isPending,
    isDismissLoading: dismissMutation.isPending,

    // Actions
    handleCancel,
    handleDismiss,
    refetch,
  };
}
