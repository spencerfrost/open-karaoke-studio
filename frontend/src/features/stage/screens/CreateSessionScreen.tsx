/**
 * CreateSessionScreen - the setup step before a session exists.
 *
 * Entering the stage used to call `joinAsHost()` silently, so the TV appeared
 * with an empty queue and a code without asking the host anything. This sits in
 * that seam: no new route, no new guard, and if recovery finds a live session it
 * never renders at all.
 *
 * Unlike its siblings in this folder it must NOT touch `useStageShell()` - it
 * renders before `StageShell` mounts, when there is no session and no queue yet.
 * It does borrow the shell's surface vocabulary (glass panel on the scrimmed
 * sunburst) so it reads as the same app, and only uses `--foreground` tints for
 * text: `--muted-foreground` is black, meant for cream cards, not this ground.
 *
 * The rotation toggle here is a deliberate, scoped exception to "the mode control
 * must not go on the TV" (docs/plans/2026-08-29-roster-and-rotation.md): there is
 * no performer yet to be confused by it. `RotationModeCard` in Settings remains
 * the only way to change a *live* session's mode.
 */

import React, { useState } from "react";
import { X } from "lucide-react";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import type { HostSessionSetup } from "@/stores/sessionStore";

/**
 * Text fields on the stage's dark ground. The base Input is built for cream
 * card surfaces: it hardcodes `placeholder:text-muted-foreground`, and that
 * token is black, so a placeholder here would be black on near-black. Override
 * it (and the near-black `border-input`) with the panel's own glass roles.
 */
const fieldClass =
  "h-12 border-glass-border/20 bg-glass/5 text-lg text-foreground placeholder:text-foreground/40";

interface CreateSessionScreenProps {
  /** Rejecting is the caller's job: it toasts and leaves this screen mounted. */
  onStart: (options: HostSessionSetup) => void | Promise<void>;
  /** The create request is in flight. Drives the hand-off screen below. */
  isStarting?: boolean;
}

const CreateSessionScreen: React.FC<CreateSessionScreenProps> = ({
  onStart,
  isStarting = false,
}) => {
  const [isRotation, setIsRotation] = useState(true);
  const [performerNames, setPerformerNames] = useState<string[]>([]);
  const [nameInput, setNameInput] = useState("");
  const [durationInput, setDurationInput] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const addName = () => {
    const trimmed = nameInput.trim();
    if (!trimmed) return;
    // The backend dedupes by normalized name anyway; this just keeps the list
    // from ever showing "Dan" twice.
    const isDuplicate = performerNames.some(
      (name) => name.toLowerCase() === trimmed.toLowerCase(),
    );
    if (!isDuplicate) {
      setPerformerNames((names) => [...names, trimmed]);
    }
    setNameInput("");
  };

  const removeName = (target: string) => {
    setPerformerNames((names) => names.filter((name) => name !== target));
  };

  const handleStart = async () => {
    if (isSubmitting) return;
    setIsSubmitting(true);
    try {
      const parsedDuration = Number.parseFloat(durationInput);
      await onStart({
        queueOrderMode: isRotation ? "rotation" : "append",
        performerNames,
        durationHours:
          durationInput.trim() && Number.isFinite(parsedDuration)
            ? parsedDuration
            : undefined,
      });
    } finally {
      // Owned here, not by the parent: a failed start toasts without remounting
      // this screen, and the button must not stay dead afterwards.
      setIsSubmitting(false);
    }
  };

  // The hand-off moment. Rendered from inside this component rather than as a
  // branch in Stage.tsx so the form above stays mounted: if the request fails,
  // the host gets their names and choices back rather than a blank screen.
  if (isStarting || isSubmitting) {
    return (
      <div className="flex w-full flex-col items-center gap-6">
        <h1 className="font-display text-4xl text-foreground">
          Creating session
        </h1>
        <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <div className="flex w-full flex-col gap-8">
      <h1 className="text-center font-display text-4xl text-foreground">
        Create a session
      </h1>

      {/* One panel, one surface. Rows are divided rather than floated apart, so
          the three settings read as one form instead of three widgets. */}
      <div className="divide-y divide-glass-border/10 rounded-md border border-glass-border/10 bg-glass/5">
        <div className="flex items-center justify-between gap-6 p-5">
          <div>
            <div className="text-xl text-foreground">Queue order</div>
            <p className="pt-1 text-base text-foreground/55">
              {isRotation
                ? "Turns alternate fairly between everyone singing."
                : "Songs play in the order they were added."}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <span className="text-lg text-foreground/80">
              {isRotation ? "Rotation" : "Append"}
            </span>
            <Switch
              checked={isRotation}
              onCheckedChange={setIsRotation}
              aria-label="Toggle rotation queue ordering"
            />
          </div>
        </div>

        <div className="space-y-3 p-5">
          <div>
            <div className="text-xl text-foreground">Singers</div>
            <p className="pt-1 text-base text-foreground/55">
              Optional. Names can be added later.
            </p>
          </div>

          <div className="flex gap-3">
            <Input
              value={nameInput}
              onChange={(e) => setNameInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addName();
                }
              }}
              placeholder="Add a name"
              maxLength={50}
              className={fieldClass + " flex-1"}
            />
            <Button
              variant="outline"
              onClick={addName}
              disabled={!nameInput.trim()}
              className="h-12 px-6 text-lg"
            >
              Add
            </Button>
          </div>

          {performerNames.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {performerNames.map((name) => (
                <button
                  key={name}
                  type="button"
                  onClick={() => removeName(name)}
                  aria-label={`Remove ${name}`}
                  className="flex items-center gap-2 rounded-full border border-glass-border/20 bg-glass/10 px-4 py-1.5 text-lg text-foreground transition-colors hover:bg-glass/20"
                >
                  {name}
                  <X className="size-4 text-foreground/50" />
                </button>
              ))}
            </div>
          )}
        </div>

        <Accordion type="single" collapsible>
          <AccordionItem value="advanced" className="border-none">
            <AccordionTrigger className="px-5 text-base text-foreground/55 hover:no-underline">
              Advanced
            </AccordionTrigger>
            <AccordionContent className="px-5">
              <div className="flex items-center justify-between gap-6">
                <label
                  htmlFor="session-length"
                  className="text-lg text-foreground"
                >
                  Session length
                  <span className="block pt-1 text-base text-foreground/55">
                    Hours. Tonight only — your saved default is unchanged.
                  </span>
                </label>
                <Input
                  id="session-length"
                  type="number"
                  min={0.5}
                  step={0.5}
                  value={durationInput}
                  onChange={(e) => setDurationInput(e.target.value)}
                  placeholder="Default"
                  className={fieldClass + " w-32 shrink-0"}
                />
              </div>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </div>

      <Button
        variant="primary"
        onClick={handleStart}
        className="h-16 w-full text-2xl"
      >
        Create Session
      </Button>
    </div>
  );
};

export default CreateSessionScreen;
