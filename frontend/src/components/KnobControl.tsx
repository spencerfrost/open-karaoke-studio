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
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [startY, setStartY] = useState(0);
  const [startValue, setStartValue] = useState(0);
  const knobRef = useRef<HTMLDivElement>(null);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
    setStartY(e.clientY);
    setStartValue(value);
    document.body.style.cursor = "ns-resize";
  }, [value]);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging) return;
    
    e.preventDefault();
    const deltaY = startY - e.clientY; // Inverted: drag up = positive
    const deltaSteps = Math.round(deltaY / sensitivity);
    const newValue = Math.max(min, Math.min(max, startValue + (deltaSteps * step)));
    
    if (newValue !== value) {
      onChange(newValue);
    }
  }, [isDragging, startY, startValue, sensitivity, step, min, max, value, onChange]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
    document.body.style.cursor = "auto";
  }, []);

  // Touch events for mobile
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    e.preventDefault();
    const touch = e.touches[0];
    setIsDragging(true);
    setStartY(touch.clientY);
    setStartValue(value);
  }, [value]);

  const handleTouchMove = useCallback((e: TouchEvent) => {
    if (!isDragging) return;
    
    e.preventDefault();
    const touch = e.touches[0];
    const deltaY = startY - touch.clientY; // Inverted: drag up = positive
    const deltaSteps = Math.round(deltaY / sensitivity);
    const newValue = Math.max(min, Math.min(max, startValue + (deltaSteps * step)));
    
    if (newValue !== value) {
      onChange(newValue);
    }
  }, [isDragging, startY, startValue, sensitivity, step, min, max, value, onChange]);

  const handleTouchEnd = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Add/remove event listeners
  React.useEffect(() => {
    if (isDragging) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      document.addEventListener("touchmove", handleTouchMove, { passive: false });
      document.addEventListener("touchend", handleTouchEnd);
      
      return () => {
        document.removeEventListener("mousemove", handleMouseMove);
        document.removeEventListener("mouseup", handleMouseUp);
        document.removeEventListener("touchmove", handleTouchMove);
        document.removeEventListener("touchend", handleTouchEnd);
      };
    }
  }, [isDragging, handleMouseMove, handleMouseUp, handleTouchMove, handleTouchEnd]);

  // Calculate rotation angle based on value (for visual feedback)
  const rotation = ((value - startValue) * 2) % 360; // 2 degrees per unit change

  return (
    <div className={`flex flex-col items-center gap-2 ${className}`}>
      <div className="text-sm font-medium text-lemon-chiffon">{label}</div>
      
      <div className="flex items-center gap-2">
        {/* Reset button */}
        {onReset && (
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
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
            relative w-16 h-16 rounded-full bg-gradient-to-br from-gray-600 to-gray-800 
            border-2 border-gray-500 cursor-ns-resize select-none
            ${isDragging ? "ring-2 ring-orange-peel" : ""}
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
              transformOrigin: "50% 30px", // Rotate around center of knob
            }}
          />
          
          {/* Center dot */}
          <div className="absolute top-1/2 left-1/2 w-2 h-2 bg-gray-400 rounded-full transform -translate-x-1/2 -translate-y-1/2" />
        </div>
      </div>
      
      {/* Value display */}
      <div className="text-lg font-mono text-lemon-chiffon">
        {value > 0 ? '+' : ''}{value}{unit}
      </div>
      
      {/* Instructions */}
      <div className="text-xs text-lemon-chiffon/60 text-center">
        Drag up/down to adjust
      </div>
    </div>
  );
};

export default KnobControl;