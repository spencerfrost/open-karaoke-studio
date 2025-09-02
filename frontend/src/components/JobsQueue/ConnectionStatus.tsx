import React from "react";
import { ConnectionStatusProps } from "./JobsQueue.types";

const ConnectionStatus: React.FC<ConnectionStatusProps> = ({ isConnected }) => {
  return (
    <div className="flex items-center gap-2 mt-2">
      {isConnected ? (
        <div className="flex items-center gap-1 text-green-600">
          <div className="w-2 h-2 bg-green-600 rounded-full animate-pulse"></div>
          <span className="text-xs">Live</span>
        </div>
      ) : (
        <div className="flex items-center gap-1 text-yellow-600">
          <div className="w-2 h-2 bg-yellow-600 rounded-full"></div>
          <span className="text-xs">Connecting</span>
        </div>
      )}
    </div>
  );
};

export default ConnectionStatus;
