import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";

interface BaseResultCardProps {
  thumbnail: string;
  title: string;
  subtitle: string;
  duration?: string;
  isLoading?: boolean;
  isSubmitted?: boolean;
  onSelect: () => void;
  existsInLibrary?: boolean;
  children?: React.ReactNode;
  disabled?: boolean;
}

export const BaseResultCard: React.FC<BaseResultCardProps> = ({
  thumbnail,
  title,
  subtitle,
  duration,
  isLoading = false,
  isSubmitted = false,
  onSelect,
  existsInLibrary = false,
  children,
  disabled,
}) => {
  return (
    <Card className="overflow-hidden hover:shadow-md transition-shadow py-2">
      <CardContent className="px-2 sm:px-4">
        {/* Mobile: Vertical Layout, Desktop: Horizontal Layout */}
        <div className="flex flex-col sm:flex-row gap-2 sm:gap-4">
          {/* Content */}
          <div className="flex-1 min-w-0 flex gap-4">
            {/* Thumbnail */}
            <div className="w-12 h-12 sm:w-16 sm:h-16 rounded overflow-hidden">
              <img
                src={thumbnail}
                alt={title}
                className="w-full h-full object-cover"
                loading="lazy"
              />
            </div>
            <div>
              <h3
                className="font-medium text-foreground line-clamp-2 mb-0.5 sm:mb-1 text-sm sm:text-base"
                title={title}
              >
                {title}
              </h3>
              <p
                className="text-xs sm:text-sm text-muted-foreground line-clamp-1"
                title={subtitle}
              >
                {subtitle}
              </p>
              {duration && (
                <p className="text-xs text-muted-foreground mt-0.5 sm:mt-1">
                  {duration}
                </p>
              )}
              {children && <div className="mt-1 sm:mt-2">{children}</div>}
            </div>
          </div>

          {/* Action Button */}
          <div className="flex-shrink-0 flex items-center justify-center w-full sm:w-auto">
            <Button
              onClick={onSelect}
              disabled={disabled || isLoading || isSubmitted || existsInLibrary}
              variant="default"
              size="sm"
              className="w-full sm:w-auto"
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Adding...
                </>
              ) : isSubmitted ? (
                "Queued"
              ) : existsInLibrary ? (
                "Already Added"
              ) : (
                "Add to Library"
              )}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
