/**
 * GuidedTour - the live demo's walk through the main loop, on the stage.
 *
 * Only in demo sessions: it renders nothing unless this device is the stage
 * of a demo pool account's session, so a normal night never sees it.
 *
 * The steps (see tourSteps) move when the app does something, never on a
 * "Next" click. The first card asks for the sound to be turned on, and that
 * click is also the page's first user gesture, which the stage needs before
 * it will start a song by itself (useSongStart's reload guard). After a reload
 * mid-tour the browser forgets that gesture, so the sound card comes back
 * until it's pressed again; the tour itself resumes on the step it was on.
 *
 * Mounted inside StageShell, so it sits inside the full-screen container and
 * can use the shell's screen and queue.
 */

import React, { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { useAccess } from "@/hooks/useAccess";
import { useSongs } from "@/hooks/api/useSongs";
import {
  useStageQueue,
  useStageScreen,
  useStageShell,
} from "@/features/stage/StageShellContext";
import { useSessionStore } from "@/stores/sessionStore";
import { tourKeyFor, tourStepFor, useTourStore } from "@/stores/tourStore";
import type { Song } from "@/types/Song";
import {
  FALLBACK_COPY,
  MIX_WITHOUT_PHONE_BODY,
  STEP_COPY,
  type StepCopy,
} from "../tourCopy";
import {
  afterSoundOn,
  nextStep,
  pickFallbackSong,
  type TourStep,
} from "../tourSteps";
import { useTourSignals } from "../useTourSignals";
import { useTourTargets } from "../useTourTargets";
import FallbackSong from "./FallbackSong";
import TourCard from "./TourCard";
import TourEndCard from "./TourEndCard";
import TourLayer from "./TourLayer";

/** Library songs looked at when choosing one to offer instead. */
const FALLBACK_POOL_SIZE = 60;

/** Whether the page has had a click yet (always true where the API is missing). */
function hasUserActivation(): boolean {
  return !navigator.userActivation || navigator.userActivation.hasBeenActive;
}

const GuidedTour: React.FC = () => {
  const { isDemo, isStageDevice } = useAccess();
  const sessionId = useSessionStore((s) => s.sessionId);
  const createdAt = useSessionStore((s) => s.sessionInfo?.created_at);
  // When the demo's time runs out the stage clears the session and signs the
  // visitor out; sessionId goes null and the tour simply unmounts, leaving
  // the stage's own "Your demo has ended" and the redirect to /join alone.
  if (!isDemo || !isStageDevice || !sessionId || !createdAt) return null;
  const tourKey = tourKeyFor(sessionId, createdAt);
  // Keyed, so a new session starts with fresh readings.
  return <TourRunner key={tourKey} sessionId={sessionId} tourKey={tourKey} />;
};

const TourRunner: React.FC<{ sessionId: string; tourKey: string }> = ({
  sessionId,
  tourKey,
}) => {
  const step = useTourStore((s) => tourStepFor(s.steps, tourKey));
  const setStoredStep = useTourStore((s) => s.setStep);
  const { signals, fallback, failedSongIds } = useTourSignals(sessionId, step);

  const setStep = (next: TourStep) => setStoredStep(tourKey, next);

  // Follow the app.
  const next = nextStep(step, signals);
  useEffect(() => {
    if (next !== step) setStoredStep(tourKey, next);
  }, [next, step, tourKey, setStoredStep]);

  // The sound card: the first step, and again after a reload until clicked.
  const [activated, setActivated] = useState(hasUserActivation);
  const finished = step === "end" || step === "done";
  const showSound = step === "sound" || (!activated && !finished);
  const handleSoundOn = () => {
    setActivated(true);
    if (step === "sound") setStep(afterSoundOn(signals));
  };

  // Song select is where the processing list and Sing this live. A fresh
  // stage rests on the player, so bring the wheel up once per step that
  // needs it - unless a song is loaded or the visitor is elsewhere already.
  const shell = useStageShell();
  const screen = useStageScreen();
  const queue = useStageQueue();
  const openedFor = useRef<TourStep | null>(null);
  const hasCurrent = Boolean(queue?.current);
  useEffect(() => {
    if (step !== "wheel" && step !== "ready") return;
    if (openedFor.current === step) return;
    openedFor.current = step;
    if (screen?.name === "performance" && !hasCurrent) shell?.openSelect();
  }, [step, screen?.name, hasCurrent, shell]);

  // A library song to offer when the visitor's own can't be had.
  const { useSongs: useSongList } = useSongs();
  const { data: library } = useSongList(
    {
      limit: String(FALLBACK_POOL_SIZE),
      sort_by: "date_added",
      direction: "desc",
    },
    { enabled: fallback !== null, staleTime: 5 * 60 * 1000 },
  );
  const fallbackSong: Song | null =
    fallback && Array.isArray(library)
      ? pickFallbackSong(library, sessionId, failedSongIds)
      : null;

  let copy: StepCopy | undefined = STEP_COPY[showSound ? "sound" : step];
  let content: React.ReactNode = null;
  let centered = false;

  if (showSound) {
    centered = true;
  } else if (fallback) {
    const fb = FALLBACK_COPY[fallback];
    copy = {
      ...fb,
      targets: ["processing-list"],
      side: "bottom",
      align: "start",
    };
    content = fallbackSong ? (
      <FallbackSong song={fallbackSong} />
    ) : (
      <p className="text-sm text-muted-foreground">
        Pick anything on the wheel.
      </p>
    );
  } else if (step === "mix" && signals.singerOnControls === null && copy) {
    copy = { ...copy, body: MIX_WITHOUT_PHONE_BODY };
  }

  const ringIds = copy ? [...copy.targets, ...(copy.ringOnly ?? [])] : [];
  const measuredIds =
    copy?.anchor && !ringIds.includes(copy.anchor)
      ? [...ringIds, copy.anchor]
      : ringIds;
  const measured = useTourTargets(
    step === "done" || showSound ? [] : measuredIds,
  );

  if (step === "done") return null;

  const skip = () => setStep("done");

  if (step === "end" && !showSound) {
    return (
      <TourLayer rings={[]} anchorId={null} centered cardKey="end">
        <TourEndCard onFinish={skip} />
      </TourLayer>
    );
  }

  if (!copy) return null;

  const onScreen = (id: string) => measured.some((b) => b.id === id);
  const anchorId =
    copy.anchor && onScreen(copy.anchor)
      ? copy.anchor
      : (copy.targets.find(onScreen) ?? null);

  return (
    <TourLayer
      rings={measured.filter((b) => ringIds.includes(b.id))}
      anchorId={anchorId}
      side={copy.side}
      align={copy.align}
      centered={centered}
      cardKey={showSound ? "sound" : `${step}:${fallback ?? ""}`}
    >
      <TourCard
        title={copy.title}
        body={copy.body}
        how={copy.how}
        docsPage={copy.docsPage}
        onSkip={skip}
      >
        {showSound ? (
          <Button
            variant="primary"
            size="lg"
            onClick={handleSoundOn}
            className="self-start"
          >
            Sound is on
          </Button>
        ) : (
          content
        )}
      </TourCard>
    </TourLayer>
  );
};

export default GuidedTour;
