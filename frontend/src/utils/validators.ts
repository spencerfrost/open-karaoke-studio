/**
 * Check if a file is an audio file
 */
export const isAudioFile = (file: File): boolean => {
  const audioTypes = [
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/ogg",
    "audio/flac",
    "audio/aac",
    "audio/m4a",
  ];
  return audioTypes.includes(file.type);
};

/**
 * Validate YouTube URL
 */
export const isValidYouTubeUrl = (url: string): boolean => {
  const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.?be)\/.+$/;
  return youtubeRegex.test(url);
};

/**
 * Extract video ID from YouTube URL
 */
export const extractYouTubeVideoId = (url: string): string | null => {
  if (!isValidYouTubeUrl(url)) return null;

  // Match patterns like youtube.com/watch?v=VIDEO_ID or youtu.be/VIDEO_ID
  const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&]+)/);
  return match ? match[1] : null;
};

/**
 * Validate singer name
 */
export const isValidSingerName = (name: string): boolean => {
  return name.trim().length > 0 && name.trim().length <= 128;
};

/**
 * Validate song title
 */
export const isValidSongTitle = (title: string): boolean => {
  return title.trim().length > 0 && title.trim().length <= 256;
};
