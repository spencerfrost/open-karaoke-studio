/**
 * Format seconds into MM:SS format
 */
export const formatTime = (
  seconds: number,
  showMs: boolean = false,
): string => {
  if (isNaN(seconds) || seconds < 0) return "0:00";
  const totalSeconds = Math.floor(seconds);
  const mins = Math.floor(totalSeconds / 60);
  const secs = totalSeconds % 60;
  if (showMs) {
    const msPart = Math.round((seconds - totalSeconds) * 1000);
    return `${mins}:${secs < 10 ? "0" : ""}${secs}.${msPart.toString().padStart(3, "0")}`;
  }
  return `${mins}:${secs < 10 ? "0" : ""}${secs}`;
};

/**
 * Parse a "h:mm:ss" / "mm:ss" / "ss" duration string into seconds.
 * Returns 0 for unparseable input. Inverse of formatTime.
 */
export const parseDurationToSeconds = (duration: string): number => {
  const parts = duration.split(":").map(Number);
  // A negative component means the string was malformed (e.g. a stray leading
  // minus); fail safe to 0 rather than emit a negative duration downstream.
  if (parts.some((part) => Number.isNaN(part) || part < 0)) return 0;
  if (parts.length === 3) {
    return parts[0] * 3600 + parts[1] * 60 + parts[2];
  } else if (parts.length === 2) {
    return parts[0] * 60 + parts[1];
  } else if (parts.length === 1) {
    return parts[0];
  }
  return 0;
};

/**
 * Format a date string to a readable format
 */
export const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(date);
};

/**
 * Format a file size in bytes to a human-readable format
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return "0 Bytes";

  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
};

/**
 * Truncate a string with ellipsis if it exceeds the max length
 */
export const truncateText = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + "...";
};

/**
 * Format a date string as a relative time (e.g., "2h ago", "just now")
 */
export const formatRelativeTime = (dateString: string): string => {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSecs < 60) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return formatDate(dateString);
};
