import type { JobStep } from "@/types/Song";

/** What a pipeline step is doing, in a first-time guest's words. */
const STEP_LABELS: Record<JobStep, string> = {
  download: "Getting the song",
  separate: "Taking out the vocals",
  align: "Timing the lyrics",
};

export function stepLabel(step: JobStep | null | undefined): string {
  return step ? STEP_LABELS[step] : "Getting it ready";
}

export const WAITING_LABEL = "Waiting its turn";
