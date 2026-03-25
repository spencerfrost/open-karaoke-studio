/**
 * PlayerErrorBoundary - Error boundary for graceful player error handling
 * Provides recovery mechanisms and user-friendly error messages
 */

import { Component, ErrorInfo, ReactNode } from "react";
import { Button } from "@/components/ui/button";
import type { PlayerError } from "../KaraokePlayer.types";
import { createLogger } from "@/lib/logger";

const logger = createLogger("component:player-error-boundary");

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: PlayerError) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

class PlayerErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    logger.error("Player Error Boundary caught an error:", error, errorInfo);

    if (this.props.onError) {
      this.props.onError({
        code: "COMPONENT_ERROR",
        message: error.message,
        details: { error, errorInfo },
      });
    }
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default error UI
      return (
        <div className="flex flex-col items-center justify-center h-full text-center p-8">
          <div className="text-red-500 text-lg font-semibold mb-4">
            Karaoke Player Error
          </div>
          <div className="text-background/70 mb-6 max-w-md">
            {this.state.error?.message ||
              "Something went wrong with the player."}
          </div>
          <div className="space-x-4">
            <Button onClick={this.handleRetry} variant="outline">
              Try Again
            </Button>
            <Button onClick={() => window.location.reload()} variant="ghost">
              Reload Page
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default PlayerErrorBoundary;
