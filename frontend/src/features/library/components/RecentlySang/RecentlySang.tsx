import React, { useState } from "react";
import { usePerformanceHistory } from "@/hooks/api/usePerformanceHistory";
import { formatRelativeTime } from "@/utils/formatters";
import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight } from "lucide-react";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import { createLogger } from "@/lib/logger";

const logger = createLogger("component:RecentlySang");

const PAGE_SIZE = 20;

const RecentlySang: React.FC = () => {
  const [offset, setOffset] = useState(0);
  const { data, isLoading } = usePerformanceHistory(PAGE_SIZE, offset);

  const total = data?.total ?? 0;
  const items = data?.items ?? [];
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE);

  logger.debug("Rendering RecentlySang", { total, currentPage });

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner size={24} />
      </div>
    );
  }

  if (total === 0) {
    return (
      <div className="text-center py-12 text-lemon-chiffon/50">
        No performances yet. Start a session and play some songs!
      </div>
    );
  }

  return (
    <div className="mb-8 w-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        {totalPages > 1 && (
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              disabled={currentPage === 0}
              className="text-orange-peel hover:bg-orange-peel/20 disabled:opacity-30"
            >
              <ChevronLeft size={16} />
              Previous
            </Button>
            <span className="text-sm text-lemon-chiffon/80 px-2">
              {currentPage + 1} of {totalPages}
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setOffset(offset + PAGE_SIZE)}
              disabled={currentPage >= totalPages - 1}
              className="text-orange-peel hover:bg-orange-peel/20 disabled:opacity-30"
            >
              Next
              <ChevronRight size={16} />
            </Button>
          </div>
        )}
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-lemon-chiffon/20 text-lemon-chiffon/60">
              <th className="text-left pb-2 pr-4 font-medium">Song</th>
              <th className="text-left pb-2 pr-4 font-medium">Artist</th>
              <th className="text-left pb-2 pr-4 font-medium">Singer</th>
              <th className="text-left pb-2 pr-4 font-medium">Session</th>
              <th className="text-left pb-2 font-medium">When</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr
                key={item.id}
                className="border-b border-lemon-chiffon/10 hover:bg-lemon-chiffon/5"
              >
                <td className="py-2 pr-4 text-lemon-chiffon">
                  {item.song_title ?? <span className="text-lemon-chiffon/40">Deleted song</span>}
                </td>
                <td className="py-2 pr-4 text-lemon-chiffon/80">
                  {item.artist ?? "—"}
                </td>
                <td className="py-2 pr-4 text-lemon-chiffon/80">{item.singer_name}</td>
                <td className="py-2 pr-4 text-lemon-chiffon/60 font-mono text-xs">
                  {item.session_code ?? "—"}
                </td>
                <td className="py-2 text-lemon-chiffon/60 text-xs">
                  {formatRelativeTime(item.performed_at)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default RecentlySang;
