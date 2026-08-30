/**
 * AccountCard - log in as a host, or log out. The account's only home.
 *
 * Host login used to live on the session-entry screen, next to a "Create
 * Session as Host" button. Stage mode deleted that screen's host half, and
 * logout had no other call site anywhere in the app - so it lands here, in
 * Settings, as a plain account section rather than a session control.
 */

import React from "react";
import { LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { LoginForm } from "@/components/auth/LoginForm";
import { useAuthStore } from "@/stores/authStore";
import { useSessionStore } from "@/stores/sessionStore";

const AccountCard: React.FC = () => {
  const { isAuthenticated, user, logout } = useAuthStore();
  const { sessionId, clearSession } = useSessionStore();

  const handleLogout = () => {
    // Logging out of the account should not leave a stage session bound to it
    // half-attached in this browser.
    if (sessionId) clearSession();
    logout();
  };

  return (
    <div className="bg-card text-card-foreground shadow-lg border border-border overflow-hidden mb-4 p-4 rounded-lg">
      <h2 className="text-xl mb-3">Account</h2>

      {isAuthenticated ? (
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="font-medium">{user?.displayName || "Host"}</div>
            <p className="text-sm opacity-75">
              Signed in — you can start a session from the stage.
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={handleLogout}>
            <LogOut className="h-4 w-4 mr-2" />
            Log out
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-sm opacity-75">
            Sign in to host a night — running the stage needs a host account.
          </p>
          <LoginForm />
        </div>
      )}
    </div>
  );
};

export default AccountCard;
