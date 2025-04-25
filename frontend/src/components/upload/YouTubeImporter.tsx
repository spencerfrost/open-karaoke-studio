import React, { useState } from "react";
import {
  isValidYouTubeUrl,
  extractYouTubeVideoId,
} from "../../utils/validators";
import vintageTheme from "../../utils/theme";
import { fetchParsedMetadata } from "@/services/youtubeService";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

interface YouTubeImporterProps {
  onYouTubeImport: (url: string, title?: string, artist?: string) => void;
}

const YouTubeImporter: React.FC<YouTubeImporterProps> = ({
  onYouTubeImport,
}) => {
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [artist, setArtist] = useState("");
  const [showMetadata, setShowMetadata] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const colors = vintageTheme.colors;

  // Card style
  const cardStyle = {
    backgroundColor: colors.lemonChiffon,
    color: colors.russet,
    boxShadow: `0 4px 6px rgba(0, 0, 0, 0.1), inset 0 0 0 1px ${colors.orangePeel}`,
  };

  // Button style
  const buttonStyle = {
    backgroundColor: colors.orangePeel,
    color: colors.russet,
    border: `1px solid ${colors.lemonChiffon}`,
  };

  // Input style
  const inputStyle = {
    backgroundColor: `${colors.lemonChiffon}80`,
    borderColor: colors.orangePeel,
    color: colors.russet,
  };

  // Handle URL input
  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setUrl(e.target.value);
    if (error) setError(null);
  };

  // Validate and proceed
  const handleNext = async () => {
    if (!url.trim()) {
      setError("Please enter a YouTube URL");
      return;
    }

    if (!isValidYouTubeUrl(url)) {
      setError("Please enter a valid YouTube URL");
      return;
    }

    // Try to extract video ID to further validate
    const videoId = extractYouTubeVideoId(url);
    if (!videoId) {
      setError("Could not extract video ID from URL");
      return;
    }

    setError(null);

    try {
      const response = await fetchParsedMetadata(videoId);
      setTitle(response.title);
      setArtist(response.artist);
      setShowMetadata(true);
    } catch (error) {
      setError("Failed to fetch metadata. Please try again.");
    }
  };

  // Handle final submission
  const handleSubmit = () => {
    if (!url.trim() || !isValidYouTubeUrl(url)) {
      setError("Please enter a valid YouTube URL");
      return;
    }

    onYouTubeImport(url, title || undefined, artist || undefined);

    // Reset form
    setUrl("");
    setTitle("");
    setArtist("");
    setShowMetadata(false);
  };

  // Back to URL input
  const handleBack = () => {
    setShowMetadata(false);
  };

  return (
    <div className="w-full rounded-lg p-4" style={cardStyle}>
      <h3 className="text-md font-medium mb-3">YouTube URL</h3>

      {!showMetadata ? (
        // Step 1: URL input
        <div>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Paste YouTube URL here"
              className="flex-1 border rounded px-3 py-2 focus:outline-none"
              style={inputStyle}
              value={url}
              onChange={handleUrlChange}
            />
            <button
              className="px-4 py-2 rounded transition-colors hover:opacity-90"
              style={buttonStyle}
              onClick={handleNext}
            >
              Next
            </button>
          </div>
          {error && (
            <div
              className="mt-2 p-2 rounded text-sm"
              style={{
                backgroundColor: `${colors.rust}20`,
                color: colors.rust,
              }}
            >
              {error}
            </div>
          )}

          {/* YouTube thumbnail preview */}
          {url && isValidYouTubeUrl(url) && extractYouTubeVideoId(url) && (
            <div className="mt-3">
              <div className="aspect-video bg-gray-200 rounded overflow-hidden">
                <img
                  src={`https://img.youtube.com/vi/${extractYouTubeVideoId(url)}/0.jpg`}
                  alt="YouTube video thumbnail"
                  className="w-full h-full object-cover"
                />
              </div>
            </div>
          )}
        </div>
      ) : (
        // Step 2: Metadata input
        <Dialog open={showMetadata} onOpenChange={setShowMetadata}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Confirm Metadata</DialogTitle>
            </DialogHeader>
            <div className="space-y-3">
              <div>
                <label className="block text-sm mb-1">Video Title</label>
                <input
                  type="text"
                  placeholder="Enter video title (optional)"
                  className="w-full border rounded px-3 py-2 focus:outline-none"
                  style={inputStyle}
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-sm mb-1">Artist</label>
                <input
                  type="text"
                  placeholder="Enter artist name (optional)"
                  className="w-full border rounded px-3 py-2 focus:outline-none"
                  style={inputStyle}
                  value={artist}
                  onChange={(e) => setArtist(e.target.value)}
                />
              </div>
            </div>
            <div className="flex gap-2 mt-4">
              <button
                className="px-4 py-2 rounded transition-colors hover:opacity-90 flex-1"
                style={{
                  backgroundColor: "transparent",
                  border: `1px solid ${colors.orangePeel}`,
                  color: colors.russet,
                }}
                onClick={handleBack}
              >
                Back
              </button>
              <button
                className="px-4 py-2 rounded transition-colors hover:opacity-90 flex-1"
                style={buttonStyle}
                onClick={handleSubmit}
              >
                Process Video
              </button>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};

export default YouTubeImporter;
