import React from "react";
import { cn } from "@/lib/utils";
import { useWorkerStatus } from "./hooks/useBatchJobs";

/** One chip per Celery queue: is a worker serving it? */
const WorkerStrip: React.FC = () => {
  const { data, isLoading } = useWorkerStatus();

  if (isLoading) {
    return <p className="text-sm text-foreground-dim">Checking workers…</p>;
  }
  if (!data?.brokerReachable) {
    return (
      <p className="w-fit rounded bg-destructive px-3 py-1 text-sm text-destructive-foreground">
        Can't reach the job queue (Redis), so nothing here will run.
      </p>
    );
  }

  return (
    <div className="flex flex-wrap gap-2">
      {data.queues.map(({ queue, workers }) => {
        const up = workers.length > 0;
        return (
          <span
            key={queue}
            title={up ? workers.join(", ") : "No worker is serving this queue"}
            className={cn(
              "flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs",
              up
                ? "border-success/40 text-foreground"
                : "border-destructive bg-destructive text-destructive-foreground",
            )}
          >
            <span
              className={cn(
                "h-2 w-2 rounded-full",
                up ? "bg-success" : "bg-destructive-foreground",
              )}
            />
            {queue} worker {up ? "running" : "not running"}
          </span>
        );
      })}
    </div>
  );
};

export default WorkerStrip;
