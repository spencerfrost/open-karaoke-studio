/**
 * Performance feature exports
 * Clean API for performance controls functionality
 */

// Component exports
export { default as PerformanceControlsPanel } from "./components/PerformanceControlsPanel";
export { ConnectedPerformanceControls } from "./components/ConnectedPerformanceControls";

// The stage rail's controls strip
export * from "./controls";

// Hook exports
export { usePerformanceControlsLogic } from "./hooks/usePerformanceControlsLogic";
export { useLyricsFixes } from "./hooks/useLyricsFixes";
