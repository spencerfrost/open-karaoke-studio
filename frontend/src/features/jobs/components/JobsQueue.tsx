import React from "react";
import { Drawer } from "@/components/ui/drawer";
import { useJobsQueue } from "../hooks/useJobsQueue";
import JobsQueueTrigger from "./JobsQueueTrigger";
import JobsQueueDrawer from "./JobsQueueDrawer";

const JobsQueue: React.FC = () => {
  const {
    isOpen,
    setIsOpen,
    jobs,
    isConnected,
    error,
    activeJobsCount,
    handleCancel,
    handleDismiss,
  } = useJobsQueue();

  return (
    <div className="fixed right-0 top-1/3 z-40">
      <Drawer direction="right" open={isOpen} onOpenChange={setIsOpen}>
        <JobsQueueTrigger
          isOpen={isOpen}
          onToggle={setIsOpen}
          activeJobsCount={activeJobsCount}
        />

        <JobsQueueDrawer
          isOpen={isOpen}
          onOpenChange={setIsOpen}
          jobs={jobs}
          isConnected={isConnected}
          error={error}
          onCancelJob={handleCancel}
          onDismissJob={handleDismiss}
        />
      </Drawer>
    </div>
  );
};

export default JobsQueue;
