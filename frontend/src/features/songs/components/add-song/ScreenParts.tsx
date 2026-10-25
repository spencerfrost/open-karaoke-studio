/**
 * The pieces every add-song screen is built from: the back link, the theme's
 * header decoration, section labels, and the loading and error states.
 */

import React from "react";
import { ChevronLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { HeaderDecoration } from "@/components/layout/HeaderDecoration";
import { cn } from "@/lib/utils";

export const BackLink: React.FC<{ label: string; onClick: () => void }> = ({
  label,
  onClick,
}) => (
  <Button
    variant="ghost"
    size="touch"
    onClick={onClick}
    className="text-foreground-dim hover:text-foreground -ml-3 max-w-full self-start font-semibold"
  >
    <ChevronLeft className="size-5" />
    <span className="truncate">{label}</span>
  </Button>
);

interface ScreenHeaderProps {
  back: React.ReactNode;
  children: React.ReactNode;
}

/** Back link, the screen's title block, then the theme's header decoration. */
export const ScreenHeader: React.FC<ScreenHeaderProps> = ({
  back,
  children,
}) => (
  <header className="flex flex-col gap-3">
    {back}
    {children}
    <HeaderDecoration className="-mx-4 sm:-mx-6" />
  </header>
);

export const ScreenTitle: React.FC<{
  children: React.ReactNode;
  className?: string;
}> = ({ children, className }) => (
  <h1
    className={cn(
      "font-display text-4xl leading-none break-words text-foreground",
      className,
    )}
  >
    {children}
  </h1>
);

export const SectionLabel: React.FC<{
  children: React.ReactNode;
  id?: string;
}> = ({ children, id }) => (
  <h2
    id={id}
    className="text-section-label text-sm font-extrabold tracking-widest uppercase"
  >
    {children}
  </h2>
);

/** Placeholder rows while a list loads. */
export const RowsSkeleton: React.FC<{ count?: number }> = ({ count = 5 }) => (
  <div className="flex flex-col gap-3" aria-busy="true" aria-label="Loading">
    {Array.from({ length: count }, (_, i) => (
      <div key={i} className="flex items-center gap-3">
        <Skeleton className="bg-surface size-14 rounded-lg" />
        <div className="flex flex-1 flex-col gap-2">
          <Skeleton className="bg-surface h-4 w-3/4" />
          <Skeleton className="bg-surface h-3 w-1/2" />
        </div>
      </div>
    ))}
  </div>
);

interface ScreenMessageProps {
  title: string;
  children?: React.ReactNode;
  /** Shown as a "Try again" button. */
  onRetry?: () => void;
}

/** A failed load or an empty result, in place of the list. */
export const ScreenMessage: React.FC<ScreenMessageProps> = ({
  title,
  children,
  onRetry,
}) => (
  <div role="status" className="flex flex-col items-start gap-2 py-6">
    <p className="text-lg font-semibold">{title}</p>
    {children && <p className="text-foreground-dim">{children}</p>}
    {onRetry && (
      <Button variant="outline-foreground" size="touch" onClick={onRetry}>
        Try again
      </Button>
    )}
  </div>
);
