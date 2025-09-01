import React from "react";
import { ListMusic } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DrawerTrigger } from "@/components/ui/drawer";
import { JobsQueueTriggerProps } from "./JobsQueue.types";

const JobsQueueTrigger: React.FC<JobsQueueTriggerProps> = () => {
  return (
    <DrawerTrigger asChild>
      <Button
        variant="secondary"
        size="sm"
        className="rounded-l-lg rounded-r-none bg-card/90 border border-r-0 border-border hover:bg-card shadow-lg backdrop-blur-sm w-7 h-24 flex items-center"
      >
        <ListMusic size={14} />
      </Button>
    </DrawerTrigger>
  );
};

export default JobsQueueTrigger;