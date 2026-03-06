import * as React from "react";
import * as SliderPrimitive from "@radix-ui/react-slider";

import { cn } from "@/lib/utils";

interface SliderProps
  extends React.ComponentProps<typeof SliderPrimitive.Root> {
  variant?: "default" | "performance";
}

function Slider({
  className,
  defaultValue,
  value,
  min = 0,
  max = 100,
  variant = "default",
  ...props
}: SliderProps) {
  const _values = React.useMemo(
    () =>
      Array.isArray(value)
        ? value
        : Array.isArray(defaultValue)
          ? defaultValue
          : [min, max],
    [value, defaultValue, min, max]
  );

  return (
    <SliderPrimitive.Root
      data-slot="slider"
      defaultValue={defaultValue}
      value={value}
      min={min}
      max={max}
      className={cn(
        "relative flex w-full touch-none items-center select-none data-[disabled]:opacity-50 data-[orientation=vertical]:h-full data-[orientation=vertical]:min-h-44 data-[orientation=vertical]:w-auto data-[orientation=vertical]:flex-col",
        className
      )}
      {...props}
    >
      <SliderPrimitive.Track
        data-slot="slider-track"
        className={cn(
          "bg-russet/50 relative grow overflow-hidden rounded-full data-[orientation=horizontal]:h-1.5 data-[orientation=horizontal]:w-full data-[orientation=vertical]:h-full data-[orientation=vertical]:w-1.5",
          variant === "performance" &&
            "data-[orientation=vertical]:w-2 data-[orientation=horizontal]:h-2"
        )}
      >
        <SliderPrimitive.Range
          data-slot="slider-range"
          className={cn(
            "bg-accent/80 absolute data-[orientation=horizontal]:h-full data-[orientation=vertical]:w-full"
          )}
        />
      </SliderPrimitive.Track>
      {Array.from({ length: _values.length }, (_, index) => (
        <SliderPrimitive.Thumb
          data-slot="slider-thumb"
          key={index}
          className={cn(
            "block shrink-0 border transition-[color,box-shadow] disabled:pointer-events-none disabled:opacity-50",
            variant === "default" &&
              "border-primary bg-background ring-ring/50 size-4 rounded-full shadow-sm hover:ring-4 focus-visible:ring-4 focus-visible:outline-hidden",
            variant === "performance" && [
              "relative h-14 w-24 rounded-sm",
              "bg-gradient-to-b from-orange-peel to-rust border-orange-peel/60",
              "shadow-[inset_0_2px_1px_rgba(255,200,100,0.25),inset_0_-2px_1px_rgba(0,0,0,0.45),0_4px_10px_rgba(0,0,0,0.5)]",
              "hover:shadow-[inset_0_2px_1px_rgba(255,200,100,0.35),inset_0_-2px_1px_rgba(0,0,0,0.5),0_4px_10px_rgba(0,0,0,0.5),0_0_12px_rgba(255,150,50,0.4)]",
              "focus-visible:outline-hidden",
              "after:content-[''] after:absolute after:left-3 after:right-3 after:top-1/2 after:-translate-y-1/2 after:h-px after:bg-lemon-chiffon/75 after:rounded-full after:pointer-events-none",
            ]
          )}
        />
      ))}
    </SliderPrimitive.Root>
  );
}

export { Slider };
