import React, { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Mic2, ShieldCheck, UserPlus } from "lucide-react";
import { apiSend, useApiMutation, useApiQuery } from "@/hooks/api/useApi";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface UserListItem {
  id: number;
  username: string;
  display_name: string | null;
  is_admin: boolean;
  is_host: boolean;
}

interface NewUser {
  username: string;
  displayName: string;
  password: string;
  isHost: boolean;
}

const USERS_KEY = ["admin-users"] as const;
const MIN_PASSWORD_LENGTH = 4;

function useUsers() {
  return useApiQuery<UserListItem[], typeof USERS_KEY>(USERS_KEY, "users");
}

function useSetHost() {
  const queryClient = useQueryClient();
  return useApiMutation<unknown, { userId: number; isHost: boolean }>(
    "users/:id/set-host",
    "post",
    {
      mutationFn: ({ userId, isHost }) =>
        apiSend(`users/${userId}/set-host?is_host=${isHost}`, "post"),
      onSuccess: () => queryClient.invalidateQueries({ queryKey: USERS_KEY }),
    },
  );
}

function useCreateUser() {
  const queryClient = useQueryClient();
  return useApiMutation<void, NewUser>("users/register", "post", {
    mutationFn: async ({ username, displayName, password, isHost }) => {
      const { id } = await apiSend<
        { id: number },
        { username: string; display_name?: string; password: string }
      >("users/register", "post", {
        username,
        display_name: displayName || undefined,
        password,
      });
      if (isHost) {
        await apiSend(`users/${id}/set-host?is_host=true`, "post");
      }
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: USERS_KEY }),
  });
}

const EMPTY_NEW_USER: NewUser = {
  username: "",
  displayName: "",
  password: "",
  isHost: true,
};

const AddUserDialog: React.FC = () => {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<NewUser>(EMPTY_NEW_USER);
  const createUser = useCreateUser();

  const update = (changes: Partial<NewUser>) =>
    setForm((current) => ({ ...current, ...changes }));

  const canSubmit =
    !createUser.isPending &&
    form.username.trim() !== "" &&
    form.password.length >= MIN_PASSWORD_LENGTH;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    const username = form.username.trim();
    createUser.mutate(
      { ...form, username, displayName: form.displayName.trim() },
      {
        onSuccess: () => {
          toast.success(`Added ${username}`);
          setForm(EMPTY_NEW_USER);
          setOpen(false);
        },
        onError: (error) => toast.error(error.message),
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <UserPlus className="mr-2 h-4 w-4" />
          Add user
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <DialogHeader>
            <DialogTitle>Add user</DialogTitle>
            <DialogDescription>
              They sign in with this username and password.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1">
              <Label htmlFor="new-username">
                Username <span className="text-destructive">*</span>
              </Label>
              <Input
                id="new-username"
                value={form.username}
                onChange={(e) => update({ username: e.target.value })}
                placeholder="username"
                required
                autoFocus
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="new-display-name">Display name</Label>
              <Input
                id="new-display-name"
                value={form.displayName}
                onChange={(e) => update({ displayName: e.target.value })}
                placeholder="DJ Mike"
              />
            </div>
          </div>
          <div className="space-y-1">
            <Label htmlFor="new-password">
              Password <span className="text-destructive">*</span>
            </Label>
            <Input
              id="new-password"
              type="password"
              value={form.password}
              onChange={(e) => update({ password: e.target.value })}
              placeholder={`At least ${MIN_PASSWORD_LENGTH} characters`}
              minLength={MIN_PASSWORD_LENGTH}
              required
            />
          </div>
          <div className="flex items-center gap-2">
            <Switch
              id="new-is-host"
              checked={form.isHost}
              onCheckedChange={(isHost) => update({ isHost })}
            />
            <Label htmlFor="new-is-host" className="cursor-pointer">
              Can host a night
            </Label>
          </div>

          <DialogFooter>
            <Button type="submit" disabled={!canSubmit}>
              {createUser.isPending ? "Adding…" : "Add user"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

/** Everyone with an account, and who can host. */
const AdminUsersPage: React.FC = () => {
  const { data: users, isLoading, error } = useUsers();
  const setHost = useSetHost();

  const toggleHost = (user: UserListItem) => {
    const name = user.display_name ?? user.username;
    setHost.mutate(
      { userId: user.id, isHost: !user.is_host },
      {
        onSuccess: () =>
          toast.success(
            user.is_host ? `${name} can't host now` : `${name} can host now`,
          ),
        onError: (e) => toast.error(e.message),
      },
    );
  };

  return (
    <div className="max-w-4xl space-y-4">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-foreground/70">
          Hosts can start a night from the stage. Admins can do everything.
        </p>
        <AddUserDialog />
      </div>

      {isLoading && <p className="text-sm text-foreground/70">Loading…</p>}
      {error && (
        <p className="text-sm text-destructive">
          Couldn't load users: {error.message}
        </p>
      )}

      {users && (
        <div className="rounded-lg border border-border/40">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Username</TableHead>
                <TableHead>Role</TableHead>
                <TableHead className="text-right">Can host</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="text-foreground/70">
                    No users yet.
                  </TableCell>
                </TableRow>
              )}
              {users.map((user) => (
                <TableRow key={user.id}>
                  <TableCell className="font-medium">
                    {user.display_name ?? user.username}
                  </TableCell>
                  <TableCell className="text-foreground/70">
                    @{user.username}
                  </TableCell>
                  <TableCell>
                    {user.is_admin ? (
                      <Badge variant="secondary">
                        <ShieldCheck />
                        Admin
                      </Badge>
                    ) : user.is_host ? (
                      <Badge variant="accent">
                        <Mic2 />
                        Host
                      </Badge>
                    ) : (
                      <span className="text-foreground/70">Singer</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    {/* Admins always can; the switch would do nothing. */}
                    {!user.is_admin && (
                      <Switch
                        checked={user.is_host}
                        onCheckedChange={() => toggleHost(user)}
                        disabled={setHost.isPending}
                        aria-label={`${user.display_name ?? user.username} can host`}
                      />
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
};

export default AdminUsersPage;
