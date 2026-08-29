/**
 * Performance feature exports
 * Clean API for performance controls functionality
 */

// Component exports
export { default as PerformanceControlsPanel } from "./components/PerformanceControlsPanel";
export { default as KnobControl } from "./components/KnobControl";
export { ConnectedPerformanceControls } from "./components/ConnectedPerformanceControls";

// Shared controls strip — rendered by the stage rail and the phone alike
export * from "./controls";

// Hook exports
export { usePerformanceControlsLogic } from "./hooks/usePerformanceControlsLogic";
