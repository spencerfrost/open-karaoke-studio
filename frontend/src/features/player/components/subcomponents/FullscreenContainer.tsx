/**
 * FullscreenContainer - Wrapper component that handles fullscreen functionality
 * Manages fullscreen state, events, and cross-browser compatibility
 */

import React from "react";

interface FullscreenContainerProps {
  children: React.ReactNode;
  isFullscreen: boolean;
  containerRef: React.RefObject<HTMLDivElement | null>;
  fsError: string | null;
  className?: string;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
  onMouseMove?: () => void;
}

const FullscreenContainer: React.FC<FullscreenContainerProps> = ({
  children,
  isFullscreen,
  containerRef,
  fsError,
  className = "",
  onMouseEnter,
  onMouseLeave,
  onMouseMove,
}) => {
  return (
    <div
      ref={containerRef}
      className={`h-full w-full ${className} relative`}
      tabIndex={-1}
      style={{ outline: isFullscreen ? "none" : undefined }}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      onMouseMove={onMouseMove}
    >
      {/* Fullscreen Error Display */}
      {fsError && (
        <div className="absolute top-12 right-2 z-30 bg-red-500 text-white text-xs px-2 py-1 rounded shadow">
          {fsError}
        </div>
      )}

      {children}
    </div>
  );
};

export default FullscreenContainer;
