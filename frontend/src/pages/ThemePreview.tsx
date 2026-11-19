/**
 * ThemePreview - /theme: every colour role and the real stage components, in
 * any theme, with a made-up night instead of a session.
 *
 * Setting up eight phones and a queue just to see a theme is the slow way to
 * judge one. This page renders the actual components (not copies) from fake
 * data, inside a wrapper with its own `data-theme`, so switching here never
 * changes the theme saved in Settings. `?theme=retro` links straight to one.
 *
 * The handoff screen is `inert`: its buttons call the server for the session
 * you're in, and a preview mustn't skip anyone's real turn.
 */

import React, { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Mic, Music } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Toggle } from "@/components/ui/toggle";
import { SingerDot } from "@/components/session/SingerDot";
import StageQueueRail from "@/features/player/components/stage/StageQueueRail";
import RosterPicker from "@/features/stage/components/RosterPicker";
import HandoffScreen from "@/features/stage/screens/HandoffScreen";
import {
  DEFAULT_THEME,
  THEMES,
  isThemeName,
  type ThemeName,
} from "@/lib/themes";
import { singerSwatchKey, swatchText, swatchTile } from "@/lib/swatch";
import { cn } from "@/lib/utils";
import type {
  KaraokeQueueItemWithSong,
  SessionTurn,
} from "@/types/KaraokeQueue";
import type { SessionPerformer } from "@/types/SessionPerformer";
import type { Song } from "@/types/Song";

// ---- The made-up night ------------------------------------------------------

/**
 * Eight singers, so the six swatches have to repeat: ids 101 and 107 share a
 * colour, and so do 102 and 108, as people will in a real room of eight.
 */
const ROSTER: SessionPerformer[] = [
  "Sam",
  "Priya",
  "Jordan",
  "Mei",
  "Alex",
  "Tomás",
  "Riley",
  "Noor",
].map((name, i) => ({ id: 101 + i, name, seat: i, is_active: true }));

const SONGS: Song[] = [
  ["Midnight Static", "The Neon Saints"],
  ["Paper Planes Over Ohio", "June Harbor"],
  ["Cassette Heart", "Velvet Arcade"],
  ["Slow Burn Summer", "Marisol & The Tides"],
  ["Ghost Lights", "Northbound"],
  ["Rollerdisco", "Sunday Static"],
  ["Mountain Radio", "Ellis Crane"],
  ["Last Train Home", "The Low Hours"],
  ["Copper Moon", "Ada Vale"],
].map(([title, artist], i) => ({
  id: `preview-${i}`,
  title,
  artist,
  duration: 200 + i * 13,
  status: "processed",
}));

const item = (
  n: number,
  performer: SessionPerformer | null,
  singer = performer?.name ?? "",
): KaraokeQueueItemWithSong => ({
  id: String(900 + n),
  songId: SONGS[n].id,
  singer,
  performerId: performer?.id ?? null,
  position: n,
  addedAt: "2026-11-18T20:00:00Z",
  song: SONGS[n],
});

const CURRENT = item(0, ROSTER[0]);
/** The next lap, plus a song from before the roster (no id: the name picks its colour). */
const UPCOMING = [
  ...ROSTER.slice(1).map((p, i) => item(i + 1, p)),
  item(8, null, "Grandpa Joe"),
];

/** Priya's up, and the circle starts with her. */
const turnFor = (hasSong: boolean): SessionTurn => ({
  kind: hasSong ? "queued" : "empty_seat",
  performerId: ROSTER[1].id,
  performerName: ROSTER[1].name,
  itemId: hasSong ? Number(UPCOMING[0].id) : null,
  circle: [...ROSTER.slice(1), ROSTER[0]].map(({ id, name }) => ({ id, name })),
});

// ---- Pieces -----------------------------------------------------------------

const ROLE_CHIPS: { label: string; className: string }[] = [
  { label: "background", className: "bg-background text-foreground" },
  { label: "card", className: "bg-card text-card-foreground" },
  { label: "surface", className: "bg-surface text-surface-foreground" },
  { label: "surface-raised", className: "bg-surface-raised text-foreground" },
  { label: "surface-hover", className: "bg-surface-hover text-foreground" },
  { label: "muted", className: "bg-muted text-muted-foreground" },
  { label: "primary", className: "bg-primary text-primary-foreground" },
  { label: "secondary", className: "bg-secondary text-secondary-foreground" },
  { label: "accent", className: "bg-accent text-accent-foreground" },
  { label: "selected", className: "bg-selected text-selected-foreground" },
  { label: "ring", className: "bg-ring text-foreground" },
  {
    label: "destructive",
    className: "bg-destructive text-destructive-foreground",
  },
  { label: "success", className: "bg-success text-success-foreground" },
  { label: "warning", className: "bg-warning text-warning-foreground" },
  { label: "info", className: "bg-info text-info-foreground" },
];

const SWATCHES = [
  "bg-swatch-1",
  "bg-swatch-2",
  "bg-swatch-3",
  "bg-swatch-4",
  "bg-swatch-5",
  "bg-swatch-6",
];

const Section: React.FC<{
  title: string;
  note?: string;
  children: React.ReactNode;
}> = ({ title, note, children }) => (
  <section className="space-y-4">
    <div>
      <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-section-label">
        {title}
      </h2>
      {note && <p className="mt-1 text-sm text-foreground-faint">{note}</p>}
    </div>
    {children}
  </section>
);

/** The current app theme, as `useApplyTheme` set it on <html>. */
const appTheme = (): ThemeName => {
  const value = document.documentElement.dataset.theme;
  return isThemeName(value) ? value : DEFAULT_THEME;
};

// ---- Page -------------------------------------------------------------------

const ThemePreview: React.FC = () => {
  const [params, setParams] = useSearchParams();
  const requested = params.get("theme");
  const theme: ThemeName = isThemeName(requested) ? requested : appTheme();

  const [singer, setSinger] = useState(ROSTER[1].name);
  const [showOther, setShowOther] = useState(false);
  const [hasSong, setHasSong] = useState(true);
  const [toggled, setToggled] = useState(true);
  const [fader, setFader] = useState([70]);

  return (
    <div
      data-theme={theme}
      className="min-h-full bg-background px-4 py-6 text-foreground sm:px-8"
    >
      <div className="mx-auto max-w-6xl space-y-10">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="font-display text-3xl">Theme preview</h1>
            <p className="text-sm text-foreground-dim">
              A made-up night with eight singers. Switching here doesn't change
              your saved theme.
            </p>
          </div>
          <Tabs
            value={theme}
            onValueChange={(value) => setParams({ theme: value })}
          >
            <TabsList>
              {THEMES.map((t) => (
                <TabsTrigger key={t.id} value={t.id}>
                  {t.label}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        </header>

        <Section title="Roles">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
            {ROLE_CHIPS.map((chip) => (
              <div
                key={chip.label}
                className={cn(
                  "rounded-md border border-border px-3 py-4 text-sm font-medium",
                  chip.className,
                )}
              >
                {chip.label}
              </div>
            ))}
          </div>
          <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
            <span className="text-foreground">foreground</span>
            <span className="text-foreground-dim">foreground-dim</span>
            <span className="text-foreground-faint">foreground-faint</span>
            <span className="text-section-label">section-label</span>
            <span className="text-secondary">secondary text</span>
            <span className="text-accent">accent text</span>
          </div>
        </Section>

        <Section
          title="Swatches"
          note="The colours a theme gives things: singers, and songs or artists with no art."
        >
          <div className="flex flex-wrap gap-3">
            {SWATCHES.map((bg, i) => (
              <div key={bg} className="flex items-center gap-3">
                <span className={cn("size-10 rounded-full", bg)} />
                <span
                  className={cn(
                    "flex size-10 items-center justify-center rounded-md",
                    swatchTile(i),
                  )}
                >
                  <Music className="size-5" />
                </span>
              </div>
            ))}
          </div>
        </Section>

        <Section title="Controls">
          <div className="flex flex-wrap items-center gap-2">
            {(
              [
                "primary",
                "secondary",
                "accent",
                "outline",
                "ghost",
                "pill",
                "link",
                "destructive",
              ] as const
            ).map((variant) => (
              <Button key={variant} variant={variant}>
                {variant}
              </Button>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {(
              [
                "default",
                "secondary",
                "accent",
                "outline",
                "ghost",
                "destructive",
              ] as const
            ).map((variant) => (
              <Badge key={variant} variant={variant}>
                {variant}
              </Badge>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-6">
            <Toggle pressed={toggled} onPressedChange={setToggled}>
              Toggle
            </Toggle>
            <Switch checked={toggled} onCheckedChange={setToggled} />
            <Tabs defaultValue="one">
              <TabsList variant="line">
                <TabsTrigger value="one">Tab one</TabsTrigger>
                <TabsTrigger value="two">Tab two</TabsTrigger>
              </TabsList>
            </Tabs>
            <Input placeholder="Search songs" className="w-56" />
          </div>
          <div className="grid max-w-xl gap-4">
            <Slider value={fader} onValueChange={setFader} max={100} />
            <Progress value={fader[0]} />
          </div>
        </Section>

        <Section
          title="Who's singing?"
          note="The picker on the stage's confirm screen and in the queue dialog. Tap a name."
        >
          <RosterPicker
            roster={ROSTER}
            value={singer}
            onChange={setSinger}
            showOther={showOther}
            onShowOtherChange={setShowOther}
          />
        </Section>

        <Section
          title="Singers"
          note="A legend, not a screen: each name with its dot and its mic colour. Six swatches, eight people, so Sam and Riley share one, and so do Priya and Noor. Grandpa Joe's song is from before the roster, so his name picks his colour."
        >
          <div className="flex flex-wrap gap-x-6 gap-y-2 text-lg">
            {[...ROSTER, { id: null, name: "Grandpa Joe" }].map((p) => (
              <span key={p.name} className="flex items-center gap-2">
                <SingerDot performerId={p.id} name={p.name} />
                {p.name}
                <Mic
                  className={cn(
                    "size-4",
                    swatchText(singerSwatchKey(p.id, p.name)),
                  )}
                />
              </span>
            ))}
          </div>
        </Section>

        <Section
          title="Stage"
          note="The handoff screen at the Shield's 960 × 540, and the right rail. Look only: the handoff screen's buttons are switched off."
        >
          <div className="flex items-center gap-3 text-sm text-foreground-dim">
            <Switch checked={hasSong} onCheckedChange={setHasSong} />
            {hasSong ? "Priya has a song queued" : "Priya hasn't picked yet"}
          </div>
          <div className="flex flex-wrap items-start gap-6">
            <div className="overflow-x-auto rounded-lg border border-border">
              <div inert className="relative h-[540px] w-[960px] bg-background">
                <HandoffScreen
                  current={null}
                  upcoming={UPCOMING}
                  turn={turnFor(hasSong)}
                  roster={ROSTER}
                  onPlayFromQueue={() => {}}
                />
              </div>
            </div>
            <div className="h-[540px] w-[340px] max-w-full">
              <StageQueueRail current={CURRENT} upcoming={UPCOMING} />
            </div>
          </div>
        </Section>
      </div>
    </div>
  );
};

export default ThemePreview;
