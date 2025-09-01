export interface JobItem {
  id: string;
  progress?: number;
  status: string;
  message?: string;
  artist?: string;
  title?: string;
}

export interface JobStatusInfo {
  label: string;
  variant: "secondary" | "default" | "destructive";
}

export interface JobsQueueTriggerProps {
  isOpen: boolean;
  onToggle: (open: boolean) => void;
  activeJobsCount: number;
}

export interface JobsQueueDrawerProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  jobs: JobItem[];
  isConnected: boolean;
  error: string | null;
  onCancelJob: (taskId: string) => void;
  onDismissJob: (taskId: string) => void;
}

export interface JobItemProps {
  job: JobItem;
  onCancel: (taskId: string) => void;
  onDismiss: (taskId: string) => void;
}

export interface ConnectionStatusProps {
  isConnected: boolean;
}

export interface EmptyStateProps {
  className?: string;
}