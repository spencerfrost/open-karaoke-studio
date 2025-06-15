import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingSpinnerProps {
  size?: number;
  className?: string;
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 16,
  className = ''
}) => {
  return (
    <Loader2
      size={size}
      className={`animate-spin ${className}`}
    />
  );
};

export default LoadingSpinner;
