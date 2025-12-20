import React from "react";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";

const ConnectionIndicator: React.FC = () => {
  const { connected } = useKaraokePlayerStore();

  return (
    <div className="flex items-center gap-1.5">
      <span
        className={`h-2 w-2 rounded-full ${
          connected ? "bg-dark-cyan animate-pulse" : "bg-rust animate-pulse"
        }`}
      />
      <span
        className={`text-xs font-medium ${
          connected ? "text-dark-cyan" : "text-rust"
        }`}
      >
        {connected ? "Live" : "Offline"}
      </span>
    </div>
  );
};

export default ConnectionIndicator;
