import * as React from "react"
import { cn } from "@/lib/utils"

interface IndeterminateProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Height variant of the progress bar */
  size?: 'sm' | 'md' | 'lg'
}

/**
 * IndeterminateProgress - A linear progress bar with sliding animation
 * Used for loading states where progress cannot be measured
 */
function IndeterminateProgress({
  className,
  size = 'md',
  ...props
}: IndeterminateProgressProps) {
  const sizeClasses = {
    sm: 'h-2',
    md: 'h-1.5',
    lg: 'h-2',
  }

  return (
    <div
      className={cn(
        "relative w-full overflow-hidden bg-black/30",
        sizeClasses[size],
        className
      )}
      role="progressbar"
      aria-busy="true"
      aria-valuemin={0}
      aria-valuemax={100}
      {...props}
    >
      <div 
        className="absolute h-full w-1/3 rounded-full bg-gradient-to-r from-dark-cyan to-orange-peel animate-[indeterminate-slide_2.5s_ease-in-out_infinite]"
      />
      <style>{`
        @keyframes indeterminate-slide {
          0% { left: -33%; }
          50% { left: 100%; }
          100% { left: -33%; }
        }
      `}</style>
    </div>
  )
}

export { IndeterminateProgress }
