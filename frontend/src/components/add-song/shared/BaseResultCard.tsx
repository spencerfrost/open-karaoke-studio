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
  onSelect: () => void;
  children?: React.ReactNode;
}

export const BaseResultCard: React.FC<BaseResultCardProps> = ({
  thumbnail,
  title,
  subtitle,
  duration,
  isLoading = false,
  onSelect,
  children,
}) => {
  return (
    <Card className="overflow-hidden hover:shadow-md transition-shadow">
      <CardContent className="p-4">
        <div className="flex gap-4">
          {/* Thumbnail */}
          <div className="w-24 h-16 bg-muted rounded overflow-hidden flex-shrink-0">
            <img
              src={thumbnail}
              alt={title}
              className="w-full h-full object-cover"
              loading="lazy"
            />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <h3
              className="font-medium text-foreground line-clamp-2 mb-1"
              title={title}
            >
              {title}
            </h3>
            <p
              className="text-sm text-muted-foreground line-clamp-1"
              title={subtitle}
            >
              {subtitle}
            </p>
            {duration && (
              <p className="text-xs text-muted-foreground mt-1">{duration}</p>
            )}
            {children && <div className="mt-2">{children}</div>}
          </div>

          {/* Action Button */}
          <div className="flex-shrink-0 self-start">
            <Button
              onClick={onSelect}
              disabled={isLoading}
              variant="default"
              size="sm"
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Adding...
                </>
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
