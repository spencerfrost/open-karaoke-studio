import React from "react";

export const EmptyState: React.FC = () => {
  return (
    <div className="mb-8 w-full">
      <div className="text-center py-8">
        <p className="text-muted-foreground">
          No songs have been added yet. Start building your library!
        </p>
      </div>
    </div>
  );
};
