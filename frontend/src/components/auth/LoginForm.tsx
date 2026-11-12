import React, { useState } from "react";
import { useAuthStore } from "@/stores/authStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle, LogIn } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

interface LoginFormProps {
  onSuccess?: () => void;
  /** "lg" is the entry screen's version: tall fields and a big button, no icon. */
  size?: "default" | "lg";
  autoFocus?: boolean;
}

export const LoginForm: React.FC<LoginFormProps> = ({
  onSuccess,
  size = "default",
  autoFocus = false,
}) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const { login } = useAuthStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      await login(username, password);
      toast.success("Signed in");
      onSuccess?.();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Invalid username or password";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  const large = size === "lg";
  const fieldClass = large
    ? "h-14 border-2 border-card-border bg-transparent px-4 text-lg font-semibold md:text-lg"
    : undefined;
  const labelClass = large ? "font-bold" : undefined;

  return (
    <form onSubmit={handleSubmit} className={large ? "space-y-5" : "space-y-4"}>
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <div className="space-y-2">
        <Label htmlFor="login-username" className={labelClass}>
          Username
        </Label>
        <Input
          id="login-username"
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder={large ? undefined : "Enter username"}
          autoComplete="username"
          autoCapitalize="none"
          autoFocus={autoFocus}
          className={fieldClass}
          required
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="login-password" className={labelClass}>
          Password
        </Label>
        <Input
          id="login-password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder={large ? undefined : "Enter password"}
          autoComplete="current-password"
          className={fieldClass}
          required
        />
      </div>
      <Button
        type="submit"
        // Empty fields are caught by `required` on submit; a disabled button
        // reads as broken, especially from across the room on the TV.
        disabled={isLoading}
        variant="primary"
        className={cn(
          "w-full",
          large &&
            "h-14 border-2 border-card-border font-display text-lg font-bold",
        )}
      >
        {isLoading ? (
          "Signing in..."
        ) : large ? (
          "Sign in"
        ) : (
          <>
            <LogIn className="h-4 w-4 mr-2" />
            Sign in
          </>
        )}
      </Button>
    </form>
  );
};
