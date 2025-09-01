import React from "react";

export const EmptyState: React.FC = () => {
  return (
    <div className="mb-8 w-full">
      <div className="flex items-center justify-between mb-4">
        <span className="text-xl font-semibold text-orange-peel">
          Recently Added
        </span>
      </div>
      <div className="text-center py-8">
        <p className="text-gray-500 dark:text-gray-400">
          No songs have been added yet. Start building your library!
        </p>
      </div>
    </div>
  );
};