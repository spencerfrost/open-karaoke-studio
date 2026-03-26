import React from "react";

interface LoadingStateProps {
  songsPerPage: number;
}

export const LoadingState: React.FC<LoadingStateProps> = ({ songsPerPage }) => {
  return (
    <div className="mb-8 w-full">
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
        {Array.from({ length: songsPerPage }).map((_, index) => (
          <div
            key={index}
            className="aspect-square bg-gray-200 dark:bg-gray-800 rounded-lg animate-pulse"
          />
        ))}
      </div>
    </div>
  );
};
