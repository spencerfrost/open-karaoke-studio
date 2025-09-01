import React from "react";
import { ListMusic, Loader2 } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
  DrawerDescription,
} from "@/components/ui/drawer";
import { JobsQueueDrawerProps } from "./JobsQueue.types";
import ConnectionStatus from "./ConnectionStatus";
import JobItem from "./JobItem";
import EmptyState from "./EmptyState";

const JobsQueueDrawer: React.FC<JobsQueueDrawerProps> = ({
  jobs,
  isConnected,
  error,
  onCancelJob,
  onDismissJob,
}) => {
  return (
    <DrawerContent className="w-96 max-w-[90vw]">
      <DrawerHeader>
        <DrawerTitle className="flex items-center gap-2">
          <ListMusic size={20} />
          Jobs Queue
        </DrawerTitle>
        <DrawerDescription>
          Songs being prepared for karaoke
        </DrawerDescription>
        <ConnectionStatus isConnected={isConnected} />
      </DrawerHeader>

      <div className="flex-1 overflow-auto px-4 pb-4">
        {/* Display error if WebSocket connection fails */}
        {error && (
          <Alert variant="destructive" className="mb-4">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Connection Status when no jobs and not connected */}
        {!isConnected && jobs.length === 0 && (
          <div className="flex items-center justify-center rounded-lg p-6 border border-border bg-card/60 text-card-foreground">
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            <span>Connecting to real-time updates...</span>
          </div>
        )}

        {/* Jobs List */}
        {jobs.length > 0 ? (
          <div className="space-y-3">
            {jobs.map((job) => (
              <JobItem
                key={job.id}
                job={job}
                onCancel={onCancelJob}
                onDismiss={onDismissJob}
              />
            ))}
          </div>
        ) : (
          <EmptyState />
        )}
      </div>
    </DrawerContent>
  );
};

export default JobsQueueDrawer;