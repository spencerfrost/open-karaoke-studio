/** The reply from POST /api/songs/{id}/analyze-vocal-range. */
export interface VocalRangeAnalysis {
  vocal_range_low: string | null;
  vocal_range_high: string | null;
  /** Why there's no sung range ("rapped", "no lead found", "one note"). */
  vocal_range_label: string | null;
}

/** What to tell the admin once a range is measured. */
export function vocalRangeMessage(data: VocalRangeAnalysis): string {
  if (data.vocal_range_low && data.vocal_range_high) {
    return `Vocal range: ${data.vocal_range_low} – ${data.vocal_range_high}`;
  }
  return `No sung range: ${data.vocal_range_label ?? "no note held long enough"}`;
}
