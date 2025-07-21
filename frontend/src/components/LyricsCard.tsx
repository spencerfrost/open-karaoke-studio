import React from "react";

interface LyricsCardProps {
  lyrics?: string;
  isSynced?: boolean;
  maxPreviewLines: number;
}

const LyricsCard: React.FC<LyricsCardProps> = ({ lyrics, isSynced = false, maxPreviewLines }) => {
  if (!lyrics)
    return (
      <span className="text-muted-foreground italic">
        No lyrics available
      </span>
    );

  // Remove timestamps for synced lyrics preview
  const cleanedLyrics = isSynced
    ? lyrics
        .split("\n")
        .map((line) => line.replace(/^\[\d+:\d+\.\d+\]/g, "").trim())
        .join("\n")
    : lyrics;

  // Only show first few lines
  const lines = cleanedLyrics.split("\n").slice(0, maxPreviewLines);
  return (
    <>
      {lines.map((line, i) => (
        <p key={i} className={line.trim() === "" ? "h-4" : ""}>
          {line}
        </p>
      ))}
      {cleanedLyrics.split("\n").length > maxPreviewLines && (
        <p className="text-muted-foreground italic mt-2 border-t pt-1">
          {cleanedLyrics.split("\n").length - maxPreviewLines} more lines (not
          shown)
        </p>
      )}
    </>
  );
};

export default LyricsCard;
