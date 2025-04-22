import React, { useEffect, useState } from "react";
import { Music, X, Loader2 } from "lucide-react"; // Added Loader2 for loading state
import { SongProcessingStatus } from "../../types/Song";
import {
  getProcessingQueue,
  cancelProcessing,
} from "../../services/uploadService";
import { Button } from "@/components/ui/button"; // Import ShadCN Button
import { Alert, AlertDescription } from "@/components/ui/alert"; // Import ShadCN Alert
import { Badge } from "@/components/ui/badge"; // Import ShadCN Badge
import { Progress } from "@/components/ui/progress"; // Import ShadCN Progress
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"; // Import ShadCN Card components
import { toast } from "sonner"; // For user feedback on cancel/error

// Removed: import vintageTheme from "../../utils/theme";

interface ProcessingQueueProps {
  className?: string;
  refreshInterval?: number; // in milliseconds
}

const ProcessingQueue: React.FC<ProcessingQueueProps> = ({
  className = "",
  refreshInterval = 5000, // Default to 5 seconds
}) => {
  const [processingItems, setProcessingItems] = useState<
    SongProcessingStatus[]
  >([]);
  const [isLoading, setIsLoading] = useState(true); // Start loading initially
  const [error, setError] = useState<string | null>(null);
  // Removed: const colors = vintageTheme.colors;

  // Fetch processing queue
  useEffect(() => {
    let isMounted = true; // Prevent state updates on unmounted component

    const fetchQueue = async () => {
      // Don't set loading to true on subsequent fetches unless needed visually
      // setIsLoading(true);
      setError(null); // Clear previous errors on fetch attempt

      try {
        const response = await getProcessingQueue();

        if (!isMounted) return; // Exit if component unmounted

        if (response.error) {
          console.error("Error fetching queue:", response.error);
          setError(response.error);
          setProcessingItems([]); // Clear items on error
        } else if (response.data) {
          // Check if response.data is an object with jobs property
          const jobs =
            "jobs" in response.data ? response.data.jobs : response.data;
          // Only update state if data has changed to prevent unnecessary re-renders
          setProcessingItems((prevItems) => {
            // Basic check for changes (can be improved with deep comparison if needed)
            if (JSON.stringify(prevItems) !== JSON.stringify(jobs)) {
              return jobs;
            }
            return prevItems;
          });
        }
      } catch (err) {
        if (!isMounted) return;
        console.error("Error fetching processing queue:", err);
        setError("Failed to load processing queue");
        setProcessingItems([]); // Clear items on error
      } finally {
        if (isMounted) {
          setIsLoading(false); // Set loading false after first fetch attempt
        }
      }
    };

    fetchQueue(); // Initial fetch
    const intervalId = setInterval(fetchQueue, refreshInterval); // Periodic refresh

    // Clean up
    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, [refreshInterval]);

  // Handle canceling a processing task
  const handleCancel = async (taskId: string) => {
    // Optimistically remove the item
    const originalItems = processingItems;
    setProcessingItems((items) => items.filter((item) => item.id !== taskId));
    toast.info(`Attempting to cancel job ${taskId.substring(0, 8)}...`);

    try {
      const response = await cancelProcessing(taskId);

      if (response.error) {
        setError(response.error);
        toast.error(`Failed to cancel job: ${response.error}`);
        // Revert optimistic update
        setProcessingItems(originalItems);
        return;
      }

      if (response.data && response.data.success) {
        toast.success(`Job ${taskId.substring(0, 8)} cancelled successfully.`);
        // Item already removed optimistically
      } else {
        // Revert if backend indicates failure differently
        toast.warning(
          `Could not confirm cancellation for job ${taskId.substring(0, 8)}.`
        );
        setProcessingItems(originalItems);
      }
    } catch (err) {
      console.error("Error canceling processing:", err);
      const errorMsg = err instanceof Error ? err.message : "Unknown error";
      setError(`Failed to cancel processing: ${errorMsg}`);
      toast.error(`Failed to cancel job: ${errorMsg}`);
      // Revert optimistic update
      setProcessingItems(originalItems);
    }
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
      case "queued":
      default:
        return { label: "Queued", variant: "secondary" };
    }
  };

  // Get progress bar color based on status
  const getProgressColorStyle = (status: string): React.CSSProperties => {
    // Use CSS variables defined in the theme (globals.css)
    const color =
      status === "error" || status === "failed"
        ? "hsl(var(--destructive))"
        : "hsl(var(--secondary))"; // Use secondary for queued/processing
    return { "--progress-indicator": color } as React.CSSProperties;
  };

  // --- Render Logic ---

  // Initial Loading State
  if (isLoading) {
    return (
      <div
        className={`flex items-center justify-center rounded-lg p-6 border border-border bg-card text-card-foreground ${className}`}
      >
        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
        <span>Loading processing queue...</span>
      </div>
    );
  }

  // Error State (after initial load)
  if (error && !processingItems.length) {
    return (
      <Alert variant="destructive" className={className}>
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  // Empty Queue State
  if (!processingItems.length) {
    return (
      <Card className={`text-center ${className}`}>
        <CardContent className="p-6">
          <p className="text-muted-foreground">No songs currently processing</p>
        </CardContent>
      </Card>
    );
  }

  // --- Display Processing Items ---
  return (
    <div className={className}>
      {/* Display error alongside items if fetch fails after initial load */}
      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card className="overflow-hidden">
        {/* Removed CardHeader/Title, but could be added back if needed */}
        <CardContent className="p-0">
          {processingItems.map((item) => {
            const statusInfo = getStatusInfo(item.status);
            return (
              <div
                key={item.id}
                className="p-3 flex items-center border-b border-border/30 last:border-b-0"
              >
                {/* Icon */}
                <div className="h-10 w-10 rounded-md flex items-center justify-center mr-3 bg-secondary/20 flex-shrink-0">
                  <Music size={20} className="text-primary" />
                </div>

                {/* Main Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-center gap-2">
                    <h4 className="font-medium truncate text-sm text-card-foreground">
                      {item.message || `Job ${item.id.substring(0, 8)}...`}
                    </h4>
                    <Badge variant={statusInfo.variant} className="flex-shrink-0">
                      {statusInfo.label}
                    </Badge>
                  </div>
                  <div className="flex items-center mt-1">
                    <Progress
                      value={item.progress ?? 0}
                      className="h-1.5 flex-1 mr-2 bg-muted/30"
                      style={getProgressColorStyle(item.status)}
                    />
                    <span className="text-xs text-muted-foreground">
                      {item.progress ?? 0}%
                    </span>
                  </div>
                  {(item.status === "error" || item.status === "failed") && (
                    <p className="text-xs mt-1 text-destructive">
                      Processing failed{" "}
                      {item.error_message ? `: ${item.error_message}` : ""}
                    </p>
                  )}

                  {/* Cancel Button */}
                  {(item.status === "queued" || item.status === "processing") && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="ml-2 text-destructive hover:bg-destructive/10 h-8 w-8 p-0 flex-shrink-0"
                      onClick={() => handleCancel(item.id)}
                      aria-label="Cancel processing"
                    >
                      <X size={16} />
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>
    </div>
  );
};

export default ProcessingQueue;
