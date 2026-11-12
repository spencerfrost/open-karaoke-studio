/**
 * AccountMenu - who this device is, and the way out.
 *
 * The page layouts (AppLayout and the admin layout) put it in the top-right
 * corner, so it's in the same spot on every page. Stage mode and the singer's
 * controls are full screen with their own way out, and go without it.
 */

import React from "react";
import { ChevronDown, LogOut, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAccess } from "@/hooks/useAccess";
import { useAuthStore } from "@/stores/authStore";
import { useSessionStore } from "@/stores/sessionStore";
import { cn } from "@/lib/utils";

interface AccountMenuProps {
  className?: string;
}

const AccountMenu: React.FC<AccountMenuProps> = ({ className }) => {
  const { canEnter, isAuthenticated, inSession, singerName } = useAccess();
  const logout = useAuthStore((state) => state.logout);
  const leaveSession = useSessionStore((state) => state.leaveSession);

  if (!canEnter) return null;

  // leaveSession tells the server this device is gone before clearing local
  // state, so the device stops being listed as connected. Once nothing grants
  // access any more, the route guard sends this device to /join.
  const handleLeaveSession = () => leaveSession();

  const handleLogout = async () => {
    // Logging out of the account should not leave a session bound to it
    // half-attached in this browser.
    if (inSession) await leaveSession();
    logout();
  };

  return (
    <div className={cn("flex justify-end", className)}>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="sm" className="max-w-40">
            <User className="size-4" />
            <span className="truncate">{singerName || "You"}</span>
            <ChevronDown className="size-4 opacity-60" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {inSession && (
            <DropdownMenuItem onSelect={handleLeaveSession}>
              <LogOut className="size-4" />
              Leave session
            </DropdownMenuItem>
          )}
          {isAuthenticated && (
            <DropdownMenuItem onSelect={handleLogout}>
              <LogOut className="size-4" />
              Log out
            </DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
};

export default AccountMenu;
