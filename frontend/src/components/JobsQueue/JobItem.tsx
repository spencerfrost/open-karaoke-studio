import React from "react";
import { Music, X, EyeOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent } from "@/components/ui/card";
import { getJobStatusInfo } from "./JobsQueue.utils";
import { JobItemProps } from "./JobsQueue.types";

const JobItem: React.FC<JobItemProps> = ({ job, onCancel, onDismiss }) => {
  const statusInfo = getJobStatusInfo(job.status);

  return (
    <Card className="overflow-hidden">
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          {/* Icon */}
          <div className="h-10 w-10 rounded-md flex items-center justify-center bg-secondary/20 flex-shrink-0">
            <Music size={20} className="text-primary" />
          </div>

          {/* Main Content */}
          <div className="flex-1 min-w-0">
            <div className="flex justify-between items-start gap-2 mb-2">
              <h4 className="font-medium text-sm text-card-foreground leading-tight">
                {job.title && job.artist
                  ? `${job.title} - ${job.artist}`
                  : job.message || `Job ${job.id}`}
              </h4>
              <Badge
                variant={statusInfo.variant}
                className="flex-shrink-0"
              >
                {statusInfo.label}
              </Badge>
            </div>
            
            <div className="flex items-center gap-2 mb-2">
              <Progress
                value={job.progress ?? 0}
                className="h-1.5 flex-1 bg-accent"
              />
              <span className="text-xs text-muted-foreground min-w-fit">
                {job.progress ?? 0}%
              </span>
            </div>
            
            {job.status === "error" && (
              <p className="text-xs text-destructive mb-2">
                Processing failed. You can dismiss this job and try again.
              </p>
            )}
            
            <div className="flex items-center justify-end gap-1">
              {/* Cancel Button - Only show for cancellable statuses */}
              {(job.status === "queued" || job.status === "processing") && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-destructive hover:bg-destructive/10 h-7 px-2"
                  onClick={() => onCancel(job.id)}
                  aria-label="Cancel processing"
                >
                  <X size={14} className="mr-1" />
                  Cancel
                </Button>
              )}
              {/* Dismiss Button - Only show for failed jobs */}
              {job.status === "error" && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-muted-foreground hover:bg-muted/50 h-7 px-2"
                  onClick={() => onDismiss(job.id)}
                  aria-label="Dismiss failed job"
                >
                  <EyeOff size={14} className="mr-1" />
                  Dismiss
                </Button>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default JobItem;