import React from "react";
import { Slider } from "@/components/ui/slider";
import { DynamicIcon, IconName } from "lucide-react/dynamic";

interface PerformanceControlInputProps {
  icon: IconName;
  label: string;
  value: number;
  valueDisplay?: React.ReactNode;
  min: number;
  max: number;
  step?: number;
  onValueChange: (value: number) => void;
  className?: string;
  children?: React.ReactNode;
}

const PerformanceControlInput: React.FC<PerformanceControlInputProps> = ({
  icon,
  label,
  value,
  valueDisplay,
  min,
  max,
  step = 1,
  onValueChange,
  className = "",
  children,
}) => (
  <div className={`flex flex-col items-center gap-4 ${className}`}>
    <div className="flex flex-col items-center gap-2">
      <DynamicIcon className="text-primary" name={icon} size={20} />
      <span>{label}</span>
      {valueDisplay && (
        <span className="ml-auto text-sm bg-primary/20 px-2 py-1 rounded text-primary">
          {valueDisplay}
        </span>
      )}
    </div>
    <div className="flex flex-col items-center gap-4 flex-1">
      <Slider
        value={[value]}
        min={min}
        max={max}
        step={step}
        orientation="vertical"
        onValueChange={([v]) => onValueChange(v)}
        className="flex-1"
      />
      {children}
    </div>
  </div>
);

export default PerformanceControlInput;
