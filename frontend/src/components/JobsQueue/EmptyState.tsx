import React from "react";
import { ListMusic } from "lucide-react";
import { EmptyStateProps } from "./JobsQueue.types";

const EmptyState: React.FC<EmptyStateProps> = ({ className = "" }) => {
  return (
    <div className={`text-center py-8 text-muted-foreground ${className}`}>
      <ListMusic size={48} className="mx-auto mb-3 opacity-50" />
      <p className="text-sm">No jobs in the queue</p>
    </div>
  );
};

export default EmptyState;