import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import AppLayout from "@/components/layout/AppLayout";
import { useAuthStore } from "@/stores/authStore";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { toast } from "sonner";
import { ShieldCheck, Mic2, UserPlus, HardDrive, ShieldAlert, Copy, Fingerprint, AlignLeft } from "lucide-react";
import { AcoustIdTab } from "@/features/songs/components/admin/AcoustIdTab";
import { LibraryAuditTab } from "@/features/songs/components/admin/LibraryAuditTab";
import { DataQualityTab } from "@/features/songs/components/admin/DataQualityTab";
import { DuplicatesTab } from "@/features/songs/components/admin/DuplicatesTab";
import { LyricsAlignmentTab } from "@/features/songs/components/admin/LyricsAlignmentTab";

interface UserListItem {
  id: number;
  username: string;
  display_name: string | null;
  is_admin: boolean;
  is_host: boolean;
}

function useUsers() {
  const { token } = useAuthStore();
  return useQuery<UserListItem[]>({
    queryKey: ["admin-users"],
    queryFn: async () => {
      const res = await fetch("/api/users", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to load users");
      return res.json();
    },
    enabled: !!token,
  });
}

function useCreateUser() {
  const { token } = useAuthStore();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      username,
      displayName,
      password,
      isHost,
    }: {
      username: string;
      displayName: string;
      password: string;
      isHost: boolean;
    }) => {
      const registerRes = await fetch("/api/users/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username,
          display_name: displayName || undefined,
          password,
        }),
      });
      if (!registerRes.ok) {
        const err = await registerRes.json().catch(() => null);
        throw new Error(err?.detail || "Failed to create user");
      }
      const { id } = await registerRes.json();

      if (isHost) {
        await fetch(`/api/users/${id}/set-host?is_host=true`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        });
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
  });
}

function useSetHost() {
  const { token } = useAuthStore();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      userId,
      isHost,
    }: {
      userId: number;
      isHost: boolean;
    }) => {
      const res = await fetch(
        `/api/users/${userId}/set-host?is_host=${isHost}`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        },
      );
      if (!res.ok) throw new Error("Failed to update user");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
  });
}

const AdminPanel: React.FC = () => {
  const { data: users, isLoading, error } = useUsers();
  const setHostMutation = useSetHost();
  const createUserMutation = useCreateUser();

  const [newUsername, setNewUsername] = useState("");
  const [newDisplayName, setNewDisplayName] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newIsHost, setNewIsHost] = useState(true);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUsername.trim() || !newPassword.trim()) return;
    createUserMutation.mutate(
      {
        username: newUsername.trim(),
        displayName: newDisplayName.trim(),
        password: newPassword,
        isHost: newIsHost,
      },
      {
        onSuccess: () => {
          toast.success(`User "${newUsername}" created`);
          setNewUsername("");
          setNewDisplayName("");
          setNewPassword("");
          setNewIsHost(true);
        },
        onError: (e) => toast.error(e.message),
      },
    );
  };

  const handleToggleHost = (user: UserListItem) => {
    setHostMutation.mutate(
      { userId: user.id, isHost: !user.is_host },
      {
        onSuccess: () =>
          toast.success(
            `${user.display_name ?? user.username} ${!user.is_host ? "granted" : "removed"} host role`,
          ),
        onError: (e) => toast.error(e.message),
      },
    );
  };

  return (
    <AppLayout>
      <div className="max-w-5xl mx-auto pb-8">
        <div className="flex items-center gap-2 mb-6">
          <ShieldCheck size={22} className="text-primary" />
          <h1 className="text-2xl font-bold">Admin Panel</h1>
        </div>

        <Tabs defaultValue="users">
          <TabsList className="mb-6">
            <TabsTrigger value="users">Users</TabsTrigger>
            <TabsTrigger value="acoustid">
              <Fingerprint className="mr-1.5 h-3.5 w-3.5" />
              AcoustID
            </TabsTrigger>
            <TabsTrigger value="audit">
              <HardDrive className="mr-1.5 h-3.5 w-3.5" />
              Library Audit
            </TabsTrigger>
            <TabsTrigger value="data-quality">
              <ShieldAlert className="mr-1.5 h-3.5 w-3.5" />
              Data Quality
            </TabsTrigger>
            <TabsTrigger value="duplicates">
              <Copy className="mr-1.5 h-3.5 w-3.5" />
              Duplicates
            </TabsTrigger>
            <TabsTrigger value="alignment">
              <AlignLeft className="mr-1.5 h-3.5 w-3.5" />
              Alignment
            </TabsTrigger>
          </TabsList>

          <TabsContent value="acoustid">
            <AcoustIdTab />
          </TabsContent>

          <TabsContent value="audit">
            <LibraryAuditTab />
          </TabsContent>

          <TabsContent value="data-quality">
            <DataQualityTab />
          </TabsContent>

          <TabsContent value="duplicates">
            <DuplicatesTab />
          </TabsContent>

          <TabsContent value="alignment">
            <LyricsAlignmentTab />
          </TabsContent>

          <TabsContent value="users">
        <div className="max-w-2xl space-y-6">
        {/* Create User Form */}
        <div className="p-4 rounded-lg bg-card border border-border/50 space-y-4">
          <h2 className="font-semibold flex items-center gap-2">
            <UserPlus size={16} />
            Add User
          </h2>
          <form onSubmit={handleCreateUser} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label htmlFor="new-username" className="text-xs">
                  Username <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="new-username"
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                  placeholder="username"
                  required
                  className="h-8 text-sm"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="new-display-name" className="text-xs">
                  Display name
                </Label>
                <Input
                  id="new-display-name"
                  value={newDisplayName}
                  onChange={(e) => setNewDisplayName(e.target.value)}
                  placeholder="DJ Mike"
                  className="h-8 text-sm"
                />
              </div>
            </div>
            <div className="space-y-1">
              <Label htmlFor="new-password" className="text-xs">
                Password <span className="text-destructive">*</span>
              </Label>
              <Input
                id="new-password"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Min 4 characters"
                minLength={4}
                required
                className="h-8 text-sm"
              />
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Switch
                  id="new-is-host"
                  checked={newIsHost}
                  onCheckedChange={setNewIsHost}
                />
                <Label htmlFor="new-is-host" className="text-sm cursor-pointer">
                  Host role
                </Label>
              </div>
              <Button
                type="submit"
                size="sm"
                disabled={
                  createUserMutation.isPending ||
                  !newUsername.trim() ||
                  newPassword.length < 4
                }
              >
                {createUserMutation.isPending ? "Creating..." : "Create user"}
              </Button>
            </div>
          </form>
        </div>

        <div className="space-y-2">
          <h2 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">
            User Management
          </h2>

          {isLoading && (
            <p className="text-sm text-muted-foreground">Loading users...</p>
          )}

          {error && (
            <p className="text-sm text-destructive">
              Failed to load users: {error.message}
            </p>
          )}

          {users && users.length === 0 && (
            <p className="text-sm text-muted-foreground">No users found.</p>
          )}

          {users && users.length > 0 && (
            <div className="space-y-2">
              {users.map((user) => (
                <div
                  key={user.id}
                  className="flex items-center gap-3 p-3 rounded-lg bg-card border border-border/50"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-sm">
                        {user.display_name ?? user.username}
                      </p>
                      {user.is_admin && (
                        <Badge variant="secondary" className="text-xs h-5">
                          <ShieldCheck size={10} className="mr-1" />
                          Admin
                        </Badge>
                      )}
                      {user.is_host && (
                        <Badge variant="outline" className="text-xs h-5">
                          <Mic2 size={10} className="mr-1" />
                          Host
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      @{user.username}
                    </p>
                  </div>

                  {!user.is_admin && (
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-xs text-muted-foreground">
                        Host
                      </span>
                      <Switch
                        checked={user.is_host}
                        onCheckedChange={() => handleToggleHost(user)}
                        disabled={setHostMutation.isPending}
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
        </div>
          </TabsContent>
        </Tabs>
      </div>
    </AppLayout>
  );
};

export default AdminPanel;
