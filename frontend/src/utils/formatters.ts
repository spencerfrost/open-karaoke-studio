/**
 * Format seconds into MM:SS format
 */
export const formatTime = (seconds: number): string => {
  if (isNaN(seconds) || seconds < 0) return "0:00";

  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs < 10 ? "0" : ""}${secs}`;
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
 * Parses a YouTube video title into separate song title and artist
 * Similar to the backend implementation but available client-side
 */
export const parseYouTubeTitle = (
  videoTitle: string,
): { title: string; artist: string } => {
  // Default values
  let artist = "Unknown Artist";
  let title = videoTitle;

  // Remove common suffixes
  const commonSuffixes = [
    "(Official Video)",
    "(Official Music Video)",
    "(Official Audio)",
    "(Lyrics)",
    "(Lyric Video)",
    "(Audio)",
    "(HQ)",
    "(HD)",
    "[Official Video]",
    "[Official Music Video]",
    "[Official Audio]",
    "[Lyrics]",
    "[Lyric Video]",
    "[Audio]",
    "[HQ]",
    "[HD]",
    "- Official Video",
    "- Lyrics",
    "(Official)",
    "[Official]",
  ];

  // Case insensitive removal of suffixes
  for (const suffix of commonSuffixes) {
    const regex = new RegExp(
      suffix.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"),
      "i",
    );
    if (regex.test(title)) {
      title = title.replace(regex, "").trim();
    }
  }

  // Try common separators
  const separators = [" - ", " – ", " | ", " _ ", ": "];
  for (const separator of separators) {
    if (title.includes(separator)) {
      const parts = title.split(separator, 2);
      artist = parts[0].trim();
      title = parts[1].trim();
      return { title, artist };
    }
  }

  // Try "by" pattern (e.g., "Title by Artist")
  if (title.toLowerCase().includes(" by ")) {
    const parts = title.toLowerCase().split(" by ", 2);
    title = parts[0].trim();
    artist = parts[1].trim();

    // Convert to title case
    title = title.replace(
      /\w\S*/g,
      (txt) => txt.charAt(0).toUpperCase() + txt.substring(1).toLowerCase(),
    );
    artist = artist.replace(
      /\w\S*/g,
      (txt) => txt.charAt(0).toUpperCase() + txt.substring(1).toLowerCase(),
    );

    return { title, artist };
  }

  // Return best guess
  return { title, artist };
};
