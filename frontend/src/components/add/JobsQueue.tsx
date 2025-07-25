import React from "react";
import { Music, X, Loader2, EyeOff } from "lucide-react";
import {
  useCancelProcessing,
  useDismissJob,
} from "../../services/uploadService";
import { useJobsWebSocket } from "@/hooks/api/useJobsWebSocket";
import { Button } from "@/components/ui/button"; // Import ShadCN Button
import { Alert, AlertDescription } from "@/components/ui/alert"; // Import ShadCN Alert
import { Badge } from "@/components/ui/badge"; // Import ShadCN Badge
import { Progress } from "@/components/ui/progress"; // Import ShadCN Progress
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { toast } from "sonner";

interface JobsQueueProps {
  className?: string;
}

const JobsQueue: React.FC<JobsQueueProps> = ({ className = "" }) => {
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
      toast.success(`Job ${taskId.substring(0, 8)} cancelled successfully.`);
      refetch();
    },
    onError: (err) => {
      console.error(err);
    },
  });

  // Use React Query for dismiss mutation
  const dismissMutation = useDismissJob({
    onSuccess: (_, taskId) => {
      toast.success(`Job ${taskId.substring(0, 8)} dismissed successfully.`);
      refetch();
    },
    onError: (err) => {
      toast.error(`Failed to dismiss job: ${err.message}`);
      console.error(err);
    },
  });

  // Handle canceling a processing task
  const handleCancel = (taskId: string) => {
    toast.info(`Attempting to cancel job ${taskId.substring(0, 8)}...`);
    cancelMutation.mutate(taskId);
  };

  // Handle dismissing a failed/completed task
  const handleDismiss = (taskId: string) => {
    toast.info(`Dismissing job ${taskId.substring(0, 8)}...`);
    dismissMutation.mutate(taskId);
  };

  // Get status label and badge variant
  const getStatusInfo = (
    status: string
  ): { label: string; variant: "secondary" | "default" | "destructive" } => {
    switch (status?.toLowerCase()) {
      case "processing":
        return { label: "Processing", variant: "default" }; // default uses primary color
      case "error":
        return { label: "Failed", variant: "destructive" };
      case "processed":
        return { label: "Completed", variant: "secondary" };
      case "queued":
      default:
        return { label: "Queued", variant: "secondary" };
    }
  };

  if (!isConnected && processingItems.length === 0) {
    return (
      <div
        className={`flex items-center justify-center rounded-lg p-6 border border-border bg-card/60 text-card-foreground ${className}`}
      >
        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
        <span>Connecting to real-time updates...</span>
      </div>
    );
  }

  // Error State (when WebSocket fails and no jobs available)
  if (error && !processingItems.length) {
    return (
      <Alert variant="destructive" className={className}>
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  // --- Display Processing Items ---
  return (
    <div className={className}>
      {/* Display error alongside items if WebSocket connection fails */}
      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card className="overflow-hidden bg-card/80 pb-0 gap-4">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Jobs Queue</CardTitle>
              <CardDescription>
                Songs being prepared for karaoke
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              {isConnected ? (
                <div className="flex items-center gap-1 text-green-600">
                  <div className="w-2 h-2 bg-green-600 rounded-full animate-pulse"></div>
                  <span className="text-xs">Live</span>
                </div>
              ) : (
                <div className="flex items-center gap-1 text-yellow-600">
                  <div className="w-2 h-2 bg-yellow-600 rounded-full"></div>
                  <span className="text-xs">Connecting</span>
                </div>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {processingItems.map((item) => {
            const statusInfo = getStatusInfo(item.status);
            return (
              <div
                key={item.id}
                className="p-3 flex items-center border-t border-black"
              >
                {/* Icon */}
                <div className="h-10 w-10 rounded-md flex items-center justify-center mr-3 bg-secondary/20 flex-shrink-0">
                  <Music size={20} className="text-primary" />
                </div>

                {/* Main Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-center gap-2">
                    <h4 className="font-medium truncate text-sm text-card-foreground">
                      {item.title && item.artist
                        ? `${item.title} - ${item.artist}`
                        : item.message || `Job ${item.id}`}
                    </h4>
                    <Badge
                      variant={statusInfo.variant}
                      className="flex-shrink-0"
                    >
                      {statusInfo.label}
                    </Badge>
                  </div>
                  <div className="flex items-center">
                    <Progress
                      value={null}
                      className="h-1.5 flex-1 mr-2 bg-accent"
                    />
                    <span className="text-xs text-muted-foreground">
                      {item.progress ?? 0}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    {item.status === "error" && (
                      <p className="text-xs mt-1 text-destructive">
                        Processing failed. You can dismiss this job and try
                        again.
                      </p>
                    )}
                    <div className="flex items-center gap-1">
                      {/* Cancel Button - Only show for cancellable statuses */}
                      {(item.status === "queued" ||
                        item.status === "processing") && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="text-destructive hover:bg-destructive/10 h-8 w-8 p-0 flex-shrink-0"
                          onClick={() => handleCancel(item.id)}
                          aria-label="Cancel processing"
                        >
                          <X size={16} />
                        </Button>
                      )}
                      {/* Dismiss Button - Only show for failed jobs */}
                      {item.status === "error" && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="text-muted-foreground hover:bg-muted/50 h-8 w-8 p-0 flex-shrink-0"
                          onClick={() => handleDismiss(item.id)}
                          aria-label="Dismiss failed job"
                        >
                          <EyeOff size={16} />
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
          {processingItems.length === 0 && (
            <div className="p-4 text-center border-t border-black">
              No jobs in the queue.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default JobsQueue;
