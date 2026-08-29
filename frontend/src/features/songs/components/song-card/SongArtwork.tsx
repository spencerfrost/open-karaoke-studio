import React from "react";
import { useNavigate } from "react-router-dom";
import { Music, Play, TriangleAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { SongArtworkProps } from "./SongCard.types";
import { useProcessingIndicators } from "@/stores/processingIndicatorsStore";
import { useSongPreview } from "../../hooks/useSongPreview";
import { ProcessingIndicator } from "./ProcessingIndicator";
import { SongPreviewOverlay } from "./SongPreviewOverlay";
import { PreviewToggleButton } from "./PreviewToggleButton";

const SyncedLyricsBadge: React.FC = () => (
  <Badge className="absolute top-2 right-2 z-10" variant="accent">
    Synced
  </Badge>
);

const AmbiguousMatchBadge: React.FC = () => {
  const navigate = useNavigate();

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigate("/admin?tab=acoustid");
  };

  return (
    <Badge
      className="absolute top-2 left-2 z-10 cursor-pointer bg-orange-500/20 text-orange-400 border border-orange-500/40 hover:bg-orange-500/30"
      variant="outline"
      onClick={handleClick}
      title="AcoustID match needs review — click to open the admin review queue"
    >
      <TriangleAlert className="size-3" />
      Needs review
    </Badge>
  );
};

export const SongArtwork: React.FC<SongArtworkProps> = ({
  song,
  artworkUrl,
  showSyncedBadge = true,
  showAmbiguousBadge = false,
  onPlay,
  showPlayButton = true,
  enablePreview = true,
  showPreviewButton = false,
}) => {
  const processingStatus = useProcessingIndicators((state) =>
    state.getStatus(song.id),
  );
  const isBlockingProcessing =
    !!processingStatus && processingStatus.engineType !== "lyrics_alignment";

  const preview = useSongPreview(song, { enabled: enablePreview });
  const previewChromeVisible = preview.isPreviewing || preview.isLoading;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    // Never leave a preview playing behind a navigation or a drawer.
    preview.stopPreview();
    onPlay?.(e);
  };

  return (
    <div
      className={cn(
        "relative overflow-hidden flex items-center justify-center bg-primary/20 cursor-pointer",
        preview.isPreviewing && "ring-2 ring-accent ring-inset",
      )}
      onClick={handleClick}
      {...preview.hoverHandlers}
    >
      {showSyncedBadge && song.syncedLyrics && <SyncedLyricsBadge />}

      {/* Yields the top-left slot to the preview chip, which sits in the same spot. */}
      {showAmbiguousBadge && !isBlockingProcessing && !previewChromeVisible && (
        <AmbiguousMatchBadge />
      )}

      {/* Play button overlay - hide if processing or showPlayButton is false */}
      {showPlayButton && !isBlockingProcessing && (
        <div className="absolute inset-0 flex items-center justify-center z-20 opacity-0 group-hover:opacity-100 transition-opacity duration-200 bg-overlay/30">
          <div className="bg-glass/20 backdrop-blur-sm rounded-full p-4">
            <Play className="w-12 h-12 text-foreground fill-foreground" />
          </div>
        </div>
      )}

      {/* Preview chrome - after the play overlay so it paints on top of it */}
      <SongPreviewOverlay
        isPreviewing={preview.isPreviewing}
        isLoading={preview.isLoading}
        progress={preview.progress}
      />

      {/* Processing indicator overlay */}
      {isBlockingProcessing && processingStatus && (
        <ProcessingIndicator status={processingStatus} variant="overlay" />
      )}

      <div className="aspect-video w-full relative">
        {artworkUrl ? (
          <>
            <img
              src={artworkUrl}
              alt=""
              aria-hidden
              className="absolute inset-0 w-full h-full object-cover scale-110 blur-md"
            />
            <img
              src={artworkUrl}
              alt={song.title}
              className="relative object-contain h-full w-full"
            />
          </>
        ) : (
          <div className="flex items-center justify-center w-full h-full aspect-video">
            <Music size={64} className="text-muted-foreground/60" />
          </div>
        )}
      </div>

      {/* Rendered last so it wins the click over the full-bleed play overlay */}
      {showPreviewButton && preview.canPreview && (
        <PreviewToggleButton
          songTitle={song.title}
          isActive={previewChromeVisible}
          onToggle={preview.togglePreview}
        />
      )}
    </div>
  );
};
