import React, { useState, useRef, useCallback } from "react";
import { RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface KnobControlProps {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  sensitivity?: number; // pixels per step
  label: string;
  unit?: string;
  onReset?: () => void;
  className?: string;
  size?: "small" | "medium" | "large" | "xl"; // Added "xl" size
}

const KnobControl: React.FC<KnobControlProps> = ({
  value,
  onChange,
  min = -Infinity,
  max = Infinity,
  step = 1,
  sensitivity = 2,
  label,
  unit = "",
  onReset,
  className = "",
  size = "medium", // Default size
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [startY, setStartY] = useState(0);
  const [startValue, setStartValue] = useState(0);
  const knobRef = useRef<HTMLDivElement>(null);

  // Define size classes
  const sizeClasses = {
    small: {
      knob: "w-12 h-12",
      indicatorOrigin: "50% 20px",
      resetBtn: "h-6 w-6",
    },
    medium: {
      knob: "w-16 h-16",
      indicatorOrigin: "50% 30px",
      resetBtn: "h-8 w-8",
    },
    large: {
      knob: "w-20 h-20",
      indicatorOrigin: "50% 40px",
      resetBtn: "h-10 w-10",
    },
    xl: {
      knob: "w-24 h-24",
      indicatorOrigin: "50% 50px",
      resetBtn: "h-12 w-12",
    }, // Extra-large size
  };

  const currentSize = sizeClasses[size];

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      setIsDragging(true);
      setStartY(e.clientY);
      setStartValue(value);
      document.body.style.cursor = "ns-resize";
    },
    [value],
  );

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isDragging) return;

      e.preventDefault();
      const deltaY = startY - e.clientY; // Inverted: drag up = positive
      const deltaSteps = Math.round(deltaY / sensitivity);
      const newValue = Math.max(
        min,
        Math.min(max, startValue + deltaSteps * step),
      );

      if (newValue !== value) {
        onChange(newValue);
      }
    },
    [
      isDragging,
      startY,
      startValue,
      sensitivity,
      step,
      min,
      max,
      value,
      onChange,
    ],
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
    document.body.style.cursor = "auto";
  }, []);

  // Touch events for mobile
  const handleTouchStart = useCallback(
    (e: React.TouchEvent) => {
      e.preventDefault();
      const touch = e.touches[0];
      setIsDragging(true);
      setStartY(touch.clientY);
      setStartValue(value);
    },
    [value],
  );

  const handleTouchMove = useCallback(
    (e: TouchEvent) => {
      if (!isDragging) return;

      e.preventDefault();
      const touch = e.touches[0];
      const deltaY = startY - touch.clientY; // Inverted: drag up = positive
      const deltaSteps = Math.round(deltaY / sensitivity);
      const newValue = Math.max(
        min,
        Math.min(max, startValue + deltaSteps * step),
      );

      if (newValue !== value) {
        onChange(newValue);
      }
    },
    [
      isDragging,
      startY,
      startValue,
      sensitivity,
      step,
      min,
      max,
      value,
      onChange,
    ],
  );

  const handleTouchEnd = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Add/remove event listeners
  React.useEffect(() => {
    if (isDragging) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      document.addEventListener("touchmove", handleTouchMove, {
        passive: false,
      });
      document.addEventListener("touchend", handleTouchEnd);

      return () => {
        document.removeEventListener("mousemove", handleMouseMove);
        document.removeEventListener("mouseup", handleMouseUp);
        document.removeEventListener("touchmove", handleTouchMove);
        document.removeEventListener("touchend", handleTouchEnd);
      };
    }
  }, [
    isDragging,
    handleMouseMove,
    handleMouseUp,
    handleTouchMove,
    handleTouchEnd,
  ]);

  // Calculate rotation angle based on value (for visual feedback)
  // One full rotation (360°) across entire -5000 to +5000 range (10000ms)
  const rotation = (value * 0.036) % 360; // 0.036 degrees per ms = realistic rotation speed

  return (
    <div className={`flex flex-col items-center gap-2 ${className}`}>
      <div className="text-sm font-medium text-lemon-chiffon">{label}</div>

      <div className="flex items-center gap-2">
        {/* Reset button */}
        {onReset && (
          <Button
            variant="ghost"
            size="icon"
            className={currentSize.resetBtn} // Dynamic size
            onClick={onReset}
            title="Reset to 0"
          >
            <RotateCcw size={16} />
          </Button>
        )}

        {/* Knob */}
        <div
          ref={knobRef}
          className={`
            relative rounded-full bg-gradient-to-br from-gray-600 to-gray-800 
            border-2 border-gray-500 cursor-ns-resize select-none
            ${currentSize.knob} ${isDragging ? "ring-2 ring-orange-peel" : ""}
            hover:ring-1 hover:ring-orange-peel/50 transition-all
          `}
          onMouseDown={handleMouseDown}
          onTouchStart={handleTouchStart}
        >
          {/* Knob indicator */}
          <div
            className="absolute top-1 left-1/2 w-1 h-4 bg-orange-peel rounded-full transform -translate-x-1/2"
            style={{
              transform: `translateX(-50%) rotate(${rotation}deg)`,
              transformOrigin: currentSize.indicatorOrigin, // Dynamic origin
            }}
          />

          {/* Center dot */}
          <div className="absolute top-1/2 left-1/2 w-2 h-2 bg-gray-400 rounded-full transform -translate-x-1/2 -translate-y-1/2" />
        </div>
      </div>

      {/* Value display */}
      <div className="text-lg font-mono text-lemon-chiffon">
        {value > 0 ? "+" : ""}
        {value}
        {unit}
      </div>
    </div>
  );
};

export default KnobControl;
