import React from "react";
import { ListMusic } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DrawerTrigger } from "@/components/ui/drawer";
import { JobsQueueTriggerProps } from "./JobsQueue.types";

const JobsQueueTrigger: React.FC<JobsQueueTriggerProps> = ({ 
  activeJobsCount 
}) => {
  return (
    <DrawerTrigger asChild>
      <Button
        variant="secondary"
        size="sm"
        className="rounded-l-lg rounded-r-none bg-card/90 border border-r-0 border-border hover:bg-card shadow-lg backdrop-blur-sm w-12 h-16 px-2 flex flex-col items-center justify-center gap-1"
      >
        <ListMusic size={14} />
        <span className="text-xs font-medium leading-none -rotate-90 whitespace-nowrap">
          Jobs
        </span>
        {activeJobsCount > 0 && (
          <Badge 
            variant="default" 
            className="absolute -top-1 -left-1 h-4 min-w-4 text-xs px-1 leading-none"
          >
            {activeJobsCount}
          </Badge>
        )}
      </Button>
    </DrawerTrigger>
  );
};

export default JobsQueueTrigger;