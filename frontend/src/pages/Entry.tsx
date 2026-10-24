import React, { useEffect, useRef, useState } from "react";
import {
  Navigate,
  useLocation,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { useSessionStore } from "@/stores/sessionStore";
import { useAuthStore } from "@/stores/authStore";
import { useDesktopLayout } from "@/hooks/useDesktopLayout";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LoginForm } from "@/components/auth/LoginForm";
import {
  SESSION_CODE_LENGTH,
  SessionCodeInput,
} from "@/features/session/components/SessionCodeInput";
import { createLogger } from "@/lib/logger";

const logger = createLogger("page:entry");

const NAME_STORAGE_KEY = "karaokeDisplayName";

/** Routes that need an account rather than a session. Arriving from one (or
 * anything under it, like each /admin/... section) opens sign-in first, with
 * a line saying why. */
const SIGN_IN_REASONS: [route: string, reason: string][] = [
  ["/stage", "Sign in to open the stage."],
  ["/settings", "Sign in to open settings."],
  ["/admin", "Sign in to open the admin pages."],
];

const signInReason = (path: string) =>
  SIGN_IN_REASONS.find(
    ([route]) => path === route || path.startsWith(`${route}/`),
  )?.[1] ?? null;

/**
 * scanned - arrived from the TV's QR code; the code is known, only a name is
 *           needed.
 * join    - typing a code from the TV.
 * signin  - a host or admin account.
 */
type View = "scanned" | "join" | "signin";

const bigButtonClass =
  "h-14 w-full border-2 border-card-border font-display text-lg font-bold";

/**
 * Entry - the app's one ungated screen (routed at /join and /join/:code).
 *
 * Two ways in: join a session with the 4-letter code from the TV (a scanned
 * QR lands here with the code already in the URL), or sign in with an
 * account. Everything else in the app requires one or the other - see
 * hooks/useAccess.ts and routes/guards.tsx.
 *
 * Which comes first is a guess from the device. A phone is almost always a
 * guest with a code, so it opens on joining; a computer or the TV is almost
 * always the host, so it opens on sign-in. Either screen links to the
 * other.
 */
const Entry: React.FC = () => {
  const params = useParams<{ code?: string }>();
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const isDesktop = useDesktopLayout();

  const codeFromUrl =
    params.code?.toUpperCase().slice(0, SESSION_CODE_LENGTH) ||
    searchParams.get("code")?.toUpperCase().slice(0, SESSION_CODE_LENGTH);

  const from =
    (location.state as { from?: { pathname: string } } | null)?.from
      ?.pathname ?? "/";
  const reason = signInReason(from);

  const [view, setView] = useState<View>(() => {
    if (codeFromUrl?.length === SESSION_CODE_LENGTH) return "scanned";
    if (codeFromUrl || !(reason || isDesktop)) return "join";
    return "signin";
  });
  const [sessionCode, setSessionCode] = useState(() => codeFromUrl || "");
  const [displayName, setDisplayName] = useState(
    () => localStorage.getItem(NAME_STORAGE_KEY) || "",
  );
  const [joinFailed, setJoinFailed] = useState(false);
  const nameInput = useRef<HTMLInputElement>(null);

  const {
    sessionId,
    isConnecting,
    connectionError,
    joinSession,
    clearSession,
  } = useSessionStore();
  const { isAuthenticated } = useAuthStore();

  // Clear any connection errors when component mounts
  useEffect(() => {
    if (connectionError) {
      clearSession();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Set once a join completes on this screen, so the redirect below fires
  // even while codeFromUrl is still truthy (see comment there).
  const [justJoined, setJustJoined] = useState(false);

  const join = async (code: string, name: string) => {
    setJoinFailed(false);
    try {
      // Joining a session implies performer role
      await joinSession(code, "performer", name);
      localStorage.setItem(NAME_STORAGE_KEY, name);
      setJustJoined(true);
    } catch (error) {
      logger.error("Failed to join session:", error);
      setJoinFailed(true);
    }
  };

  const hasAutoJoined = useRef(false);

  // Auto-join when a code arrived via the URL (a QR scan) and this browser
  // already knows a display name from a prior session. The ref guard ensures
  // this fires at most once even if dependencies change.
  useEffect(() => {
    if (hasAutoJoined.current) return;
    if (
      codeFromUrl?.length === SESSION_CODE_LENGTH &&
      displayName.trim() &&
      !sessionId &&
      !isConnecting
    ) {
      hasAutoJoined.current = true;
      logger.info("Auto-joining session from QR code", { code: codeFromUrl });
      void join(codeFromUrl, displayName.trim());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [codeFromUrl, displayName, sessionId, isConnecting]);

  // Once in, leave - unless a code is present in the URL, since that means
  // someone (possibly already signed in) is deliberately joining a session
  // via a scanned QR and needs to see the form. That only holds for a
  // session/account they already had on arrival though - once they've
  // actually joined from this screen, justJoined overrides it so they
  // proceed like everyone else.
  if ((isAuthenticated || sessionId) && (!codeFromUrl || justJoined)) {
    return <Navigate to={from} replace />;
  }

  const codeComplete = sessionCode.length === SESSION_CODE_LENGTH;

  // Join buttons stay enabled (a disabled one reads as broken from across
  // the room); pressing one early puts the cursor where something's missing.
  const focusCode = (id: string) => document.getElementById(id)?.focus();

  const handleJoin = (e: React.FormEvent) => {
    e.preventDefault();
    if (isConnecting) return;
    if (!codeComplete) return focusCode("session-code");
    if (!displayName.trim()) return nameInput.current?.focus();
    void join(sessionCode, displayName.trim());
  };

  // The compact code row beside sign-in has no name field: a browser that
  // remembers a name joins straight away, anyone else is asked for one.
  const handleQuickJoin = (e: React.FormEvent) => {
    e.preventDefault();
    if (isConnecting) return;
    if (!codeComplete) return focusCode("session-code-quick");
    if (displayName.trim()) {
      void join(sessionCode, displayName.trim());
    } else {
      setView("join");
    }
  };

  const showJoin = () => {
    setJoinFailed(false);
    setView("join");
  };

  const joinError = joinFailed && (
    <Alert variant="destructive">
      <AlertCircle className="h-4 w-4" />
      <AlertDescription>
        Couldn't join. Check the code on the TV and try again.
      </AlertDescription>
    </Alert>
  );

  const nameField = (
    <Input
      ref={nameInput}
      id="displayName"
      type="text"
      value={displayName}
      onChange={(e) => setDisplayName(e.target.value)}
      placeholder="Your name"
      maxLength={50}
      autoComplete="nickname"
      autoFocus={view === "scanned" || (view === "join" && codeComplete)}
      className="h-14 border-2 border-card-border bg-transparent px-4 text-lg font-semibold md:text-lg"
    />
  );

  const joinButton = (
    <Button type="submit" variant="primary" className={bigButtonClass}>
      {isConnecting ? "Joining..." : "Join"}
    </Button>
  );

  return (
    // Focus rings in the theme's primary, not its default ring color.
    <div className="relative flex min-h-dvh overflow-hidden text-foreground [--ring:var(--primary)] desktop:items-center desktop:justify-center desktop:px-12 desktop:py-8">
      <div className="theme-texture" />
      <div className="theme-pattern" />

      {/* Computers and the TV: two columns sharing a top and bottom edge. The
          left is the brand plus the other way in; the right is the form. */}
      <div className="relative z-10 flex w-full flex-1 desktop:grid desktop:max-w-5xl desktop:flex-none desktop:grid-cols-2 desktop:gap-16">
        {isDesktop && (
          <aside className="flex flex-col justify-between gap-10">
            <div className="space-y-4">
              <p className="font-display text-5xl font-bold leading-[1.05] text-primary xl:text-6xl">
                Open Karaoke Studio
              </p>
              <p className="text-xl text-foreground-dim">
                Start a session, run the stage, look after the library.
              </p>
            </div>

            {view === "signin" && (
              <form onSubmit={handleQuickJoin} className="space-y-3">
                <Label
                  htmlFor="session-code-quick"
                  className="text-base font-normal text-foreground-dim"
                >
                  Here to sing? Type the code from the TV.
                </Label>
                <div className="flex flex-wrap items-center gap-2">
                  <SessionCodeInput
                    id="session-code-quick"
                    variant="page"
                    value={sessionCode}
                    onChange={(code) => {
                      setSessionCode(code);
                      setJoinFailed(false);
                    }}
                  />
                  <Button
                    type="submit"
                    variant="outline-foreground"
                    className="ml-2 h-15 px-6 font-display text-base font-bold"
                  >
                    {isConnecting ? "Joining..." : "Join"}
                  </Button>
                </div>
                {joinError}
              </form>
            )}
            {view === "join" && (
              <SwitchRow
                prompt="Hosting tonight?"
                action="Sign in"
                onClick={() => setView("signin")}
              />
            )}
          </aside>
        )}

        <main className="flex flex-1 flex-col px-5 pb-8 pt-6 desktop:p-0">
          <div className="flex w-full max-w-md flex-1 flex-col self-center desktop:max-w-none">
            <p className="font-display text-lg font-bold text-primary desktop:hidden">
              Open Karaoke Studio
            </p>

            {view === "scanned" && codeFromUrl && (
              <>
                <div className="flex flex-1 flex-col items-center justify-center gap-1 py-10 text-center">
                  <p className="text-foreground-dim">You're joining</p>
                  <p className="font-accent text-[7rem] leading-none tracking-[0.14em] pl-[0.14em] text-primary [text-shadow:var(--glow-primary)]">
                    {codeFromUrl}
                  </p>
                  <p className="text-foreground-dim">the karaoke on the TV</p>
                </div>

                <Card className="px-5 sm:px-6">
                  <form onSubmit={handleJoin} className="space-y-4">
                    <div className="space-y-1">
                      <Label
                        htmlFor="displayName"
                        className="font-display text-xl font-bold"
                      >
                        What should we call you?
                      </Label>
                      <p className="text-sm text-card-foreground/75">
                        It shows on the TV when it's your turn.
                      </p>
                    </div>
                    {nameField}
                    {joinError}
                    {joinButton}
                  </form>
                </Card>

                <p className="mt-5 text-center text-foreground-dim">
                  Wrong session?{" "}
                  <Button
                    type="button"
                    variant="link"
                    onClick={showJoin}
                    className="h-auto p-0 text-base font-bold"
                  >
                    Type the code instead
                  </Button>
                </p>
              </>
            )}

            {view === "join" && (
              <>
                <header className="mt-12 space-y-2 desktop:mt-0">
                  <h1 className="font-display text-4xl font-bold">
                    Join the karaoke
                  </h1>
                  <p className="text-foreground-dim">
                    Type the 4-letter code from the TV.
                  </p>
                </header>

                <Card className="mt-7 px-5 sm:px-6 desktop:mt-6">
                  <form onSubmit={handleJoin} className="space-y-5">
                    <div className="space-y-2">
                      <Label htmlFor="session-code" className="font-bold">
                        Code from the TV
                      </Label>
                      <SessionCodeInput
                        id="session-code"
                        value={sessionCode}
                        onChange={(code) => {
                          setSessionCode(code);
                          setJoinFailed(false);
                        }}
                        onComplete={() => nameInput.current?.focus()}
                        autoFocus={!codeComplete}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="displayName" className="font-bold">
                        Your name
                      </Label>
                      {nameField}
                    </div>
                    {joinError}
                    {joinButton}
                  </form>
                </Card>

                {!isDesktop && (
                  <SwitchRow
                    prompt="Hosting tonight?"
                    action="Sign in"
                    onClick={() => setView("signin")}
                  />
                )}
              </>
            )}

            {view === "signin" && (
              <>
                <header className="mt-12 space-y-2 desktop:mt-0">
                  <h1 className="font-display text-4xl font-bold">Sign in</h1>
                  <p className="text-foreground-dim">
                    {reason ?? "For whoever's hosting."}
                  </p>
                </header>

                <Card className="mt-7 px-5 sm:px-6 desktop:mt-6">
                  <LoginForm size="lg" autoFocus={isDesktop} />
                </Card>

                {!isDesktop && (
                  <SwitchRow
                    prompt="Here to sing?"
                    action="Enter a code"
                    onClick={showJoin}
                  />
                )}
              </>
            )}
          </div>
        </main>
      </div>
    </div>
  );
};

/** The bottom row that swaps between joining and signing in. */
const SwitchRow: React.FC<{
  prompt: string;
  action: string;
  onClick: () => void;
}> = ({ prompt, action, onClick }) => (
  <div className="mt-auto space-y-4 desktop:mt-0">
    <Separator className="bg-foreground-faint" />
    <div className="flex items-center justify-between gap-3">
      <span className="text-foreground-dim">{prompt}</span>
      <Button
        type="button"
        variant="outline-foreground"
        onClick={onClick}
        className="h-12 px-5 font-display text-base font-bold"
      >
        {action}
      </Button>
    </div>
  </div>
);

export default Entry;
