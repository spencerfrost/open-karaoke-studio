import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import AppLayout from "@/components/layout/AppLayout";
import { useSessionStore } from "@/stores/sessionStore";
import { useAuthStore } from "@/stores/authStore";
import { useQueue } from "@/hooks/api/useKaraokeQueue";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import {
  Play,
  Trash2,
  SkipForward,
  Check,
  X,
  Users,
  Music,
  Settings,
} from "lucide-react";
import type { KaraokeQueueItemWithSong } from "@/types/KaraokeQueue";

interface HostSettings {
  queue_submission_mode: "instant" | "approval";
  max_songs_per_singer: number;
  queue_open: boolean;
  session_duration_hours: number;
}

function useHostSettings() {
  const { token } = useAuthStore();
  return useQuery<HostSettings>({
    queryKey: ["host-settings"],
    queryFn: async () => {
      const res = await fetch("/api/host-settings", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to load host settings");
      return res.json();
    },
    enabled: !!token,
  });
}

function useUpdateHostSettings() {
  const { token } = useAuthStore();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (settings: Partial<HostSettings>) => {
      const res = await fetch("/api/host-settings", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(settings),
      });
      if (!res.ok) throw new Error("Failed to update settings");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["host-settings"] });
    },
  });
}

function useQueueAction(path: string, method: "POST" | "DELETE" = "POST") {
  const { token } = useAuthStore();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (itemId?: string) => {
      const url = itemId ? `/api/karaoke-queue/${itemId}/${path}` : `/api/karaoke-queue/${path}`;
      const res = await fetch(url, {
        method,
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail || `Failed: ${res.statusText}`);
      }
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["karaoke-queue"] });
    },
  });
}

function useRemoveItem() {
  const { token } = useAuthStore();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (itemId: string) => {
      const res = await fetch(`/api/karaoke-queue/${itemId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to remove item");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["karaoke-queue"] });
    },
  });
}

function usePlayItem() {
  const { token } = useAuthStore();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (itemId: string) => {
      const res = await fetch(`/api/karaoke-queue/${itemId}/play`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to play item");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["karaoke-queue"] });
    },
  });
}

interface QueueItemRowProps {
  item: KaraokeQueueItemWithSong;
  onPlay: (id: string) => void;
  onRemove: (id: string) => void;
  isPending?: boolean;
  onApprove?: (id: string) => void;
  onReject?: (id: string) => void;
}

const QueueItemRow: React.FC<QueueItemRowProps> = ({
  item,
  onPlay,
  onRemove,
  isPending,
  onApprove,
  onReject,
}) => (
  <div className="flex items-center gap-3 p-3 rounded-lg bg-card border border-border/50">
    <div className="flex-1 min-w-0">
      <p className="font-medium text-sm truncate">
        {item.song?.title ?? "Unknown"}
      </p>
      <p className="text-xs text-muted-foreground truncate">
        {item.song?.artist ?? "Unknown"} &bull; Singer: {item.singer}
      </p>
    </div>
    <div className="flex items-center gap-1 shrink-0">
      {isPending ? (
        <>
          <Button
            size="icon"
            variant="ghost"
            className="h-8 w-8 text-green-500 hover:text-green-400"
            onClick={() => onApprove?.(item.id)}
            title="Approve"
          >
            <Check size={16} />
          </Button>
          <Button
            size="icon"
            variant="ghost"
            className="h-8 w-8 text-destructive hover:text-destructive/80"
            onClick={() => onReject?.(item.id)}
            title="Reject"
          >
            <X size={16} />
          </Button>
        </>
      ) : (
        <Button
          size="icon"
          variant="ghost"
          className="h-8 w-8 text-primary hover:text-primary/80"
          onClick={() => onPlay(item.id)}
          title="Play now"
        >
          <Play size={16} />
        </Button>
      )}
      <Button
        size="icon"
        variant="ghost"
        className="h-8 w-8 text-muted-foreground hover:text-destructive"
        onClick={() => onRemove(item.id)}
        title="Remove"
      >
        <Trash2 size={16} />
      </Button>
    </div>
  </div>
);

const HostDashboard: React.FC = () => {
  const { displayCode, sessionInfo } = useSessionStore();
  const { data: settings, isLoading: settingsLoading } = useHostSettings();
  const updateSettings = useUpdateHostSettings();
  const queueQuery = useQueue(displayCode || undefined);
  const skipMutation = useQueueAction("skip");
  const approveMutation = useQueueAction("approve");
  const rejectMutation = useQueueAction("reject", "DELETE");
  const removeMutation = useRemoveItem();
  const playMutation = usePlayItem();

  const [settingsOpen, setSettingsOpen] = useState(false);

  const activeItems = queueQuery.data?.upcoming ?? [];
  const currentItem = queueQuery.data?.current ?? null;
  const pendingItems = queueQuery.data?.pending ?? [];

  const handleSkip = () => {
    skipMutation.mutate(undefined, {
      onSuccess: () => toast.success("Skipped to next song"),
      onError: (e) => toast.error(e.message),
    });
  };

  const handlePlay = (id: string) => {
    playMutation.mutate(id, {
      onSuccess: () => toast.success("Now playing"),
      onError: (e) => toast.error(e.message),
    });
  };

  const handleRemove = (id: string) => {
    removeMutation.mutate(id, {
      onSuccess: () => toast.success("Removed from queue"),
      onError: (e) => toast.error(e.message),
    });
  };

  const handleApprove = (id: string) => {
    approveMutation.mutate(id, {
      onSuccess: () => toast.success("Song approved"),
      onError: (e) => toast.error(e.message),
    });
  };

  const handleReject = (id: string) => {
    rejectMutation.mutate(id, {
      onSuccess: () => toast.success("Song rejected"),
      onError: (e) => toast.error(e.message),
    });
  };

  const handleToggleQueueOpen = (open: boolean) => {
    updateSettings.mutate(
      { queue_open: open },
      {
        onSuccess: () =>
          toast.success(open ? "Queue opened" : "Queue closed"),
        onError: (e) => toast.error(e.message),
      },
    );
  };

  const handleSubmissionModeChange = (
    mode: "instant" | "approval",
  ) => {
    updateSettings.mutate(
      { queue_submission_mode: mode },
      {
        onSuccess: () => toast.success("Submission mode updated"),
        onError: (e) => toast.error(e.message),
      },
    );
  };

  return (
    <AppLayout>
      <div className="max-w-2xl mx-auto space-y-6 pb-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">KJ Dashboard</h1>
            {displayCode && (
              <p className="text-muted-foreground text-sm">
                Session code:{" "}
                <span className="font-mono font-bold text-primary">
                  {displayCode}
                </span>
              </p>
            )}
          </div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Users size={16} />
            <span>{sessionInfo?.device_count ?? 0} connected</span>
          </div>
        </div>

        {/* Quick Settings Bar */}
        {!settingsLoading && settings && (
          <div className="flex flex-wrap items-center gap-4 p-4 rounded-lg bg-card border border-border/50">
            <div className="flex items-center gap-2">
              <Switch
                id="queue-open"
                checked={settings.queue_open}
                onCheckedChange={handleToggleQueueOpen}
                disabled={updateSettings.isPending}
              />
              <Label htmlFor="queue-open" className="text-sm cursor-pointer">
                {settings.queue_open ? "Queue open" : "Queue closed"}
              </Label>
            </div>

            <div className="flex items-center gap-2">
              <Label className="text-sm whitespace-nowrap">Submissions:</Label>
              <Select
                value={settings.queue_submission_mode}
                onValueChange={(v) =>
                  handleSubmissionModeChange(v as "instant" | "approval")
                }
                disabled={updateSettings.isPending}
              >
                <SelectTrigger className="h-8 w-28 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="instant">Instant</SelectItem>
                  <SelectItem value="approval">Approval</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Button
              variant="ghost"
              size="sm"
              className="ml-auto"
              onClick={() => setSettingsOpen((o) => !o)}
            >
              <Settings size={14} className="mr-1" />
              {settingsOpen ? "Hide settings" : "More settings"}
            </Button>
          </div>
        )}

        {/* Extended Settings */}
        {settingsOpen && settings && (
          <div className="p-4 rounded-lg bg-card border border-border/50 space-y-4">
            <h3 className="font-semibold text-sm">Session Settings</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">
                  Max songs per singer
                </Label>
                <Select
                  value={String(settings.max_songs_per_singer)}
                  onValueChange={(v) =>
                    updateSettings.mutate({ max_songs_per_singer: Number(v) })
                  }
                >
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="0">Unlimited</SelectItem>
                    {[1, 2, 3, 4, 5, 10].map((n) => (
                      <SelectItem key={n} value={String(n)}>
                        {n}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">
                  Session duration (hours)
                </Label>
                <Select
                  value={String(settings.session_duration_hours)}
                  onValueChange={(v) =>
                    updateSettings.mutate({
                      session_duration_hours: Number(v),
                    })
                  }
                >
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {[2, 4, 6, 8, 12, 24].map((n) => (
                      <SelectItem key={n} value={String(n)}>
                        {n}h
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        )}

        {/* Now Playing */}
        {currentItem && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold flex items-center gap-2">
                <Music size={16} />
                Now Playing
              </h2>
              <Button
                size="sm"
                variant="outline"
                onClick={handleSkip}
                disabled={skipMutation.isPending}
              >
                <SkipForward size={14} className="mr-1" />
                Skip
              </Button>
            </div>
            <div className="p-3 rounded-lg bg-primary/10 border border-primary/30">
              <p className="font-medium">{currentItem.song?.title ?? "Unknown"}</p>
              <p className="text-sm text-muted-foreground">
                {currentItem.song?.artist ?? "Unknown"} &bull; Singer:{" "}
                {currentItem.singer}
              </p>
            </div>
          </div>
        )}

        {/* Pending Submissions */}
        {pendingItems.length > 0 && (
          <div className="space-y-2">
            <h2 className="font-semibold flex items-center gap-2">
              Pending Approval
              <Badge variant="secondary">{pendingItems.length}</Badge>
            </h2>
            <div className="space-y-2">
              {pendingItems.map((item: KaraokeQueueItemWithSong) => (
                <QueueItemRow
                  key={item.id}
                  item={item}
                  isPending
                  onPlay={handlePlay}
                  onRemove={handleRemove}
                  onApprove={handleApprove}
                  onReject={handleReject}
                />
              ))}
            </div>
          </div>
        )}

        {/* Active Queue */}
        <div className="space-y-2">
          <h2 className="font-semibold flex items-center gap-2">
            Up Next
            <Badge variant="outline">{activeItems.length}</Badge>
          </h2>
          {activeItems.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4 text-center">
              Queue is empty
            </p>
          ) : (
            <div className="space-y-2">
              {activeItems.map((item) => (
                <QueueItemRow
                  key={item.id}
                  item={item}
                  onPlay={handlePlay}
                  onRemove={handleRemove}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
};

export default HostDashboard;
