import React, { useEffect, useRef, useState } from "react";
import {
  Navigate,
  useLocation,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { useSessionStore } from "@/stores/sessionStore";
import { useAuthStore } from "@/stores/authStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle, Camera, Keyboard } from "lucide-react";
import { LoginForm } from "@/components/auth/LoginForm";
import { createLogger } from "@/lib/logger";
import { toast } from "sonner";

const logger = createLogger("page:entry");

/** Routes whose capability check is an account, not a session - the sign-in
 * disclosure defaults open when returning here from one of these. */
const HOST_ROUTES = [
  "/stage",
  "/settings",
  "/admin",
  "/admin/compare-three-track",
];

/**
 * Entry - the app's one ungated screen (routed at /join and /join/:code).
 *
 * Two ways in, side by side: join an existing session with a 4-letter code
 * (or a scanned QR, which lands here with the code already in the URL), or
 * sign in as a host. Everything else in the app requires one or the other -
 * see hooks/useAccess.ts and routes/guards.tsx.
 */
const Entry: React.FC = () => {
  const params = useParams<{ code?: string }>();
  const [searchParams] = useSearchParams();
  const location = useLocation();

  const codeFromUrl =
    params.code?.toUpperCase().slice(0, 4) ||
    searchParams.get("code")?.toUpperCase().slice(0, 4);

  const [sessionCode, setSessionCode] = useState(() => codeFromUrl || "");
  const [displayName, setDisplayName] = useState(() => {
    return localStorage.getItem("karaokeDisplayName") || "";
  });

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

  const hasAutoJoined = useRef(false);

  // Set once a join completes on this screen, so the redirect below fires
  // even while codeFromUrl is still truthy (see comment there).
  const [justJoined, setJustJoined] = useState(false);

  // Auto-join when a code arrived via the URL (a QR scan) and this browser
  // already knows a display name from a prior session. The ref guard ensures
  // this fires at most once even if dependencies change.
  useEffect(() => {
    if (hasAutoJoined.current) return;
    if (
      codeFromUrl?.length === 4 &&
      displayName.trim() &&
      !sessionId &&
      !isConnecting
    ) {
      hasAutoJoined.current = true;
      logger.info("Auto-joining session from QR code", { code: codeFromUrl });
      joinSession(codeFromUrl, "performer", displayName.trim())
        .then(() => {
          localStorage.setItem("karaokeDisplayName", displayName.trim());
          setJustJoined(true);
        })
        .catch((error) => {
          logger.error("Auto-join failed:", error);
          toast.error("Failed to join session. Please try manually.");
        });
    }
  }, [codeFromUrl, displayName, sessionId, isConnecting, joinSession]);

  const from =
    (location.state as { from?: { pathname: string } } | null)?.from
      ?.pathname ?? "/";

  // Once in, leave - unless a code is present in the URL, since that means
  // someone (possibly already signed in) is deliberately joining a session
  // via a scanned QR and needs to see the form. That only holds for a
  // session/account they already had on arrival though - once they've
  // actually joined from this screen, justJoined overrides it so they
  // proceed like everyone else.
  if ((isAuthenticated || sessionId) && (!codeFromUrl || justJoined)) {
    return <Navigate to={from} replace />;
  }

  const defaultOpenHostSignIn = HOST_ROUTES.includes(from) ? "host" : undefined;

  const handleJoinSession = async () => {
    if (!sessionCode.trim()) {
      toast.error("Please enter a session code");
      return;
    }

    if (!displayName.trim()) {
      toast.error("Please enter your name");
      return;
    }

    try {
      // Joining a session implies performer role
      await joinSession(
        sessionCode.trim().toUpperCase(),
        "performer",
        displayName.trim(),
      );
      localStorage.setItem("karaokeDisplayName", displayName.trim());
      setJustJoined(true);
    } catch (error) {
      logger.error("Failed to join session:", error);
      toast.error(
        "Failed to join session. Please check the code and try again.",
      );
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="vintage-texture-overlay" />
      <div className="vintage-sunburst-pattern" />
      <Card className="block p-8 rounded-lg shadow-xl border-primary max-w-md w-full relative z-10">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-display font-bold text-primary mb-2">
            Open Karaoke Studio
          </h1>
          <p className="text-muted-foreground">
            Join the karaoke session on the stage screen
          </p>
        </div>

        {/* Join Session */}
        <Card className="mb-4">
          <CardHeader>
            <CardTitle>Join Karaoke Session</CardTitle>
            <CardDescription>
              Scan the QR code on the stage screen to join
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {codeFromUrl ? (
              <div className="flex flex-col items-center gap-2 py-2">
                <span className="text-sm text-muted-foreground">
                  Joining session
                </span>
                <span className="text-4xl font-mono tracking-widest text-primary">
                  {codeFromUrl}
                </span>
              </div>
            ) : (
              <>
                <div className="flex flex-col items-center gap-3 py-4">
                  <div className="rounded-full bg-primary/10 p-6">
                    <Camera className="h-12 w-12 text-primary" />
                  </div>
                </div>

                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-card px-2 text-muted-foreground">
                      or enter code manually
                    </span>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="sessionCode">Session Code</Label>
                  <div className="relative">
                    <Keyboard className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      id="sessionCode"
                      type="text"
                      value={sessionCode}
                      onChange={(e) =>
                        setSessionCode(e.target.value.toUpperCase())
                      }
                      placeholder="ABCD"
                      maxLength={4}
                      className="uppercase text-center text-lg tracking-widest pl-10"
                    />
                  </div>
                </div>
              </>
            )}

            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="displayName">Your Name</Label>
                <Input
                  id="displayName"
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="Enter your name"
                  maxLength={50}
                  autoFocus={Boolean(codeFromUrl)}
                />
              </div>
              <Button
                onClick={handleJoinSession}
                disabled={
                  isConnecting ||
                  sessionCode.length !== 4 ||
                  !displayName.trim()
                }
                variant="accent"
                className="w-full"
              >
                {isConnecting ? "Joining..." : "Join Session"}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Host sign-in - secondary path */}
        <Accordion
          type="single"
          collapsible
          defaultValue={defaultOpenHostSignIn}
        >
          <AccordionItem value="host" className="border-none">
            <AccordionTrigger className="justify-center text-sm text-muted-foreground hover:no-underline">
              Hosting tonight? Sign in
            </AccordionTrigger>
            <AccordionContent>
              <LoginForm />
            </AccordionContent>
          </AccordionItem>
        </Accordion>

        {/* Error Display */}
        {connectionError && (
          <Alert variant="destructive" className="mt-4">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{connectionError}</AlertDescription>
          </Alert>
        )}
      </Card>
    </div>
  );
};

export default Entry;
