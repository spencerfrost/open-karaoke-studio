import React from 'react';

interface StepIndicatorProps {
  step: number;
  title: string;
  isActive: boolean;
  isCompleted: boolean;
}

export const StepIndicator: React.FC<StepIndicatorProps> = ({ 
  step, 
  title, 
  isActive, 
  isCompleted 
}) => (
  <div className="flex items-center gap-2">
    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
      isCompleted 
        ? 'bg-green-100 text-green-700 border-2 border-green-200' 
        : isActive 
          ? 'bg-blue-100 text-blue-700 border-2 border-blue-200' 
          : 'bg-gray-100 text-gray-500 border-2 border-gray-200'
    }`}>
      {step}
    </div>
    <span className={`text-sm font-medium ${
      isActive ? 'text-foreground' : 'text-muted-foreground'
    }`}>
      {title}
    </span>
  </div>
);
