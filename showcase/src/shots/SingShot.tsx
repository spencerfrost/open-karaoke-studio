import React from "react";
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Backdrop, Overlay } from "../components/Backdrop";
import { Cover, Phone, PHONE_SCREEN_W, TV_SCREEN_H, TV_SCREEN_W, Tv } from "../components/Devices";
import lyrics from "../data/lyrics.json";
import { QUEUE } from "../songs";
import beatGrid from "../data/beats.json";
import { CATPPUCCIN, CYBERPUNK, RETRO, Theme, VINTAGE, ThemeContext, primaryGlow, useTheme } from "../themes";

/**
 * The money shot. Maya's song plays on the TV with the lyrics lighting up
 * word by word (the app's own word timings). On her phone she drags
 * "Original singer" up and the voice comes back, then drops it to zero and
 * sings it herself. Then "MAKE IT YOURS.": the whole frame flips theme every
 * two beats, Cyberpunk → Retro → Catppuccin → Vintage → Cyberpunk.
 */

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const ease = Easing.inOut(Easing.cubic);

interface Word {
  text: string;
  start: number;
  end: number;
}
interface Line {
  text: string;
  start: number;
  words?: Word[];
}
const LINES: Line[] = lyrics.lines;
const MAYA = QUEUE[0];

/** The first line Maya sings with the singer up, and the one where it fades out. */
const FIRST_SUNG = LINES.findIndex((l) => l.text.startsWith("Get out"));
const FADE_LINE = LINES.findIndex((l) => l.text.startsWith("Take a step"));
/** Song time (s) of the first word sung with the singer up. */
export const FIRST_WORD_TIME = LINES[FIRST_SUNG].start;

// "Original singer" fader moves, in song time: up in the middle of the line
// before (after "Don't wait,"), so the voice is already there for "Get out";
// down across the fade line so you hear it disappear.
const LEAD_IN = LINES[FIRST_SUNG - 1].words!;
const UP = [LEAD_IN[1].end, LEAD_IN[3].end];
const DOWN = [LINES[FADE_LINE].start + 0.2, LINES[FADE_LINE].start + 1.6];

/** The "Original singer" fader, 0–1, at a song time. Drives the audio too. */
export const singerLevelAt = (songTime: number) =>
  interpolate(songTime, [UP[0], UP[1], DOWN[0], DOWN[1]], [0, 1, 1, 0], { ...clamp, easing: ease });

// ---------------------------------------------------------------------------
// TV: the lyrics screen. Like the app's stage: every line in one list, the
// active line large and bold, centred; the rest small and dimmed; long lines
// wrap.
// ---------------------------------------------------------------------------

const ACTIVE_PX = 56;
const INACTIVE_PX = 30;
const LYRICS_W = TV_SCREEN_W - 80;
const LINE_PAD = 14;
/** Rajdhani's average glyph width at 1px, for working out where lines wrap. */
const GLYPH = { bold: 0.46, regular: 0.42 };
/** A line becomes active this long before its first word. */
const LEAD = 0.3;
/** How long a line takes to grow into / shrink out of the active size. */
const GROW = 0.22;

const rowsAt = (text: string, px: number, bold: boolean, bodyWidth: number) =>
  Math.max(1, Math.ceil((text.length * px * bodyWidth * (bold ? GLYPH.bold : GLYPH.regular)) / LYRICS_W));

const LyricWord: React.FC<{ word: Word; t: number }> = ({ word, t }) => {
  const th = useTheme();
  const p = interpolate(t, [word.start, word.end], [0, 100], clamp);
  return (
    <span
      style={{
        backgroundImage: `linear-gradient(90deg, ${th.primary} ${p}%, ${th.ink} ${p}%)`,
        WebkitBackgroundClip: "text",
        backgroundClip: "text",
        color: "transparent",
        filter: p > 0 && th.neon ? `drop-shadow(0 0 12px rgba(${th.primaryRgb},0.55))` : "none",
      }}
    >
      {word.text}
    </span>
  );
};

const LyricsScreen: React.FC<{ songStart: number }> = ({ songStart }) => {
  const th = useTheme();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = songStart + frame / fps;

  // How active each line is, 0–1: grows in at its start, shrinks as the next begins.
  const activity = LINES.map((line, i) => {
    const on = interpolate(t, [line.start - LEAD, line.start - LEAD + GROW], [0, 1], { ...clamp, easing: ease });
    const next = LINES[i + 1];
    const off = next
      ? interpolate(t, [next.start - LEAD, next.start - LEAD + GROW], [0, 1], { ...clamp, easing: ease })
      : 0;
    return Math.max(0, on - off);
  });

  let top = 0;
  const layout = LINES.map((line, i) => {
    const a = activity[i];
    const px = INACTIVE_PX + (ACTIVE_PX - INACTIVE_PX) * a;
    const rows = rowsAt(line.text, px, a > 0.5, th.bodyWidth);
    const h = rows * px * 1.15 + LINE_PAD * 2;
    const box = { top, h, px, a };
    top += h;
    return box;
  });
  const weight = activity.reduce((s, a) => s + a, 0);
  const focus =
    weight > 0
      ? layout.reduce((s, b) => s + b.a * (b.top + b.h / 2), 0) / weight
      : layout[0].top + layout[0].h / 2;
  const VIEW_TOP = 110;
  const viewCenter = VIEW_TOP + (TV_SCREEN_H - VIEW_TOP) / 2;

  return (
    <AbsoluteFill style={{ background: th.page }}>
      <AbsoluteFill
        style={{ background: `radial-gradient(ellipse at 50% 120%, rgba(${th.haloRgb},0.35), transparent 65%)` }}
      />
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: VIEW_TOP,
          bottom: 0,
          overflow: "hidden",
          maskImage: "linear-gradient(to bottom, transparent, black 14%, black 86%, transparent)",
        }}
      >
        <div style={{ position: "absolute", left: 40, right: 40, top: viewCenter - VIEW_TOP - focus }}>
          {LINES.map((line, i) => {
            const b = layout[i];
            const active = b.a > 0.5;
            return (
              <div
                key={i}
                style={{
                  position: "absolute",
                  left: 0,
                  right: 0,
                  top: b.top,
                  height: b.h,
                  padding: `${LINE_PAD}px 0`,
                  textAlign: "center",
                  fontFamily: th.body,
                  fontWeight: active ? 700 : 500,
                  fontSize: b.px,
                  lineHeight: 1.15,
                  color: th.ink,
                  opacity: 0.5 + 0.5 * b.a,
                  textShadow: active ? "0 2px 12px rgba(0,0,0,0.6)" : "none",
                }}
              >
                {active && line.words
                  ? line.words.map((w, j) => (
                      <React.Fragment key={j}>
                        <LyricWord word={w} t={t} />
                        {j < line.words!.length - 1 ? " " : ""}
                      </React.Fragment>
                    ))
                  : line.text}
              </div>
            );
          })}
        </div>
      </div>
      <div style={{ position: "absolute", left: 40, top: 30, display: "flex", alignItems: "center", gap: 16 }}>
        <Cover hues={MAYA.hues} size={60} />
        <div>
          <div style={{ fontFamily: th.mono, fontSize: 18 * th.monoScale, letterSpacing: 3, color: th.dim }}>
            NOW SINGING · {MAYA.singer.toUpperCase()}
          </div>
          <div style={{ fontFamily: th.body, fontWeight: 700, fontSize: 28, color: th.ink }}>
            {MAYA.title} · {MAYA.artist}
          </div>
        </div>
      </div>
      {th.texture === "scanlines" && (
        <AbsoluteFill
          style={{
            backgroundImage: "repeating-linear-gradient(to bottom, rgba(255,255,255,0.03) 0 1px, transparent 1px 3px)",
          }}
        />
      )}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// "MAKE IT YOURS.": theme flips on the music's beat
// ---------------------------------------------------------------------------

const BEATS: number[] = beatGrid.beats;
const nearestBeat = (t: number) =>
  BEATS.reduce((best, b, i) => (Math.abs(b - t) < Math.abs(BEATS[best] - t) ? i : best), 0);

const THEME_RUN: Theme[] = [CYBERPUNK, RETRO, CATPPUCCIN, VINTAGE, CYBERPUNK];
const BEATS_PER_THEME = 2;
/** The shot ends three bars after "Gotta move with the groove" begins. */
const END_BEAT = nearestBeat(LINES[FADE_LINE + 1].start + 2.6) + 8;
/** "MAKE IT YOURS." lands early enough for every theme to get its two beats. */
const MAKE_BEAT = END_BEAT - THEME_RUN.length * BEATS_PER_THEME;
/** Song time "MAKE IT YOURS." lands. */
export const MAKE_TIME = BEATS[MAKE_BEAT];
/** Song time each theme in the run starts. */
const THEME_TIMES = THEME_RUN.map((_, i) => BEATS[MAKE_BEAT + i * BEATS_PER_THEME]);
/** Song time the shot ends: the downbeat after the last theme. */
export const SING_END_TIME = BEATS[END_BEAT];

const themeAt = (t: number) => {
  let theme = CYBERPUNK;
  THEME_TIMES.forEach((start, i) => {
    if (t >= start) theme = THEME_RUN[i];
  });
  return theme;
};

/** Shot length for a given song start time. */
export const singShotFrames = (songStart: number, fps: number) => Math.round((SING_END_TIME - songStart) * fps);

// ---------------------------------------------------------------------------
// Phone: the performance controls
// ---------------------------------------------------------------------------

const FADER_H = 330;
const THUMB_H = 44;

const Fader: React.FC<{ label: string; level: number; dragging: boolean }> = ({ label, level, dragging }) => {
  const th = useTheme();
  const thumbTop = (1 - level) * (FADER_H - THUMB_H);
  return (
    <div
      style={{
        flex: 1,
        height: 470,
        background: th.panel,
        border: "2px solid rgba(255,255,255,0.08)",
        borderRadius: th.radius + 4,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        paddingTop: 14,
        gap: 6,
      }}
    >
      <div
        style={{
          fontFamily: th.body,
          fontWeight: 700,
          fontSize: 18 / th.bodyWidth,
          color: th.ink,
          whiteSpace: "nowrap",
          lineHeight: 1.1,
        }}
      >
        {label}
      </div>
      <div style={{ fontFamily: th.mono, fontSize: 32 * th.monoScale, lineHeight: 1, color: th.primary }}>
        {Math.round(level * 100)}%
      </div>
      <div style={{ position: "relative", width: 100, height: FADER_H, marginTop: 6 }}>
        <div
          style={{
            position: "absolute",
            left: 44,
            width: 12,
            top: 0,
            height: FADER_H,
            borderRadius: 6,
            background: th.sunk,
            border: "1px solid rgba(255,255,255,0.1)",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: 44,
            width: 12,
            bottom: 0,
            height: level * (FADER_H - THUMB_H) + THUMB_H / 2,
            borderRadius: 6,
            background: th.primary,
            boxShadow: level > 0 && th.neon ? `0 0 16px rgba(${th.primaryRgb},0.6)` : "none",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: 10,
            top: thumbTop,
            width: 80,
            height: THUMB_H,
            borderRadius: 8,
            background: th.ink,
            boxShadow: "0 4px 14px rgba(0,0,0,0.5)",
          }}
        />
        {dragging && (
          <div
            style={{
              position: "absolute",
              left: 50 - 34,
              top: thumbTop + THUMB_H / 2 - 34,
              width: 68,
              height: 68,
              borderRadius: 34,
              background: "rgba(255,255,255,0.28)",
              border: "2px solid rgba(255,255,255,0.6)",
            }}
          />
        )}
      </div>
    </div>
  );
};

const ControlsScreen: React.FC<{ songStart: number }> = ({ songStart }) => {
  const th = useTheme();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = songStart + frame / fps;
  const level = singerLevelAt(t);
  const touch = 0.15;
  const dragging = (t >= UP[0] - touch && t <= UP[1] + touch) || (t >= DOWN[0] - touch && t <= DOWN[1] + touch);
  return (
    <AbsoluteFill style={{ background: th.page }}>
      <AbsoluteFill
        style={{ background: `radial-gradient(ellipse at 50% 120%, rgba(${th.primaryRgb},0.22), transparent 60%)` }}
      />
      <div style={{ position: "absolute", left: 20, right: 20, top: 58 }}>
        <div style={{ fontFamily: th.mono, fontSize: 15 * th.monoScale, letterSpacing: 2, color: th.dim }}>
          YOU'RE SINGING
        </div>
        <div style={{ fontFamily: th.display, fontSize: 22, color: th.ink, marginTop: 4 }}>{MAYA.title}</div>
      </div>
      <div style={{ position: "absolute", left: 14, right: 14, top: 140, display: "flex", gap: 10, width: PHONE_SCREEN_W - 28 }}>
        <Fader label="Original singer" level={level} dragging={dragging} />
        <Fader label="Backup singers" level={0} dragging={false} />
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------

const Accent: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const th = useTheme();
  return <span style={{ color: th.primary, textShadow: primaryGlow(th) }}>{children}</span>;
};

const Caption: React.FC<{ children: React.ReactNode; start: number; end: number; punch?: number }> = ({
  children,
  start,
  end,
  punch = 0,
}) => {
  const th = useTheme();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (frame < start || frame >= end) return null;
  const s = spring({ frame: frame - start, fps, config: { damping: 12, stiffness: 180 } });
  const out = interpolate(frame, [end - 6, end], [1, 0], clamp);
  return (
    <AbsoluteFill style={{ alignItems: "center", paddingTop: 56 }}>
      <div
        style={{
          fontFamily: th.display,
          fontSize: 80,
          color: th.ink,
          opacity: s * out,
          transform: `scale(${(1.3 - s * 0.3) * (1 + punch * 0.08)})`,
        }}
      >
        {children}
      </div>
    </AbsoluteFill>
  );
};

export const SingShot: React.FC<{ songStart: number }> = ({ songStart }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const total = singShotFrames(songStart, fps);
  const t = songStart + frame / fps;
  const toFrame = (time: number) => Math.round((time - songStart) * fps);
  const tvIn = spring({ frame, fps, config: { damping: 16, stiffness: 120 } });
  const phoneIn = spring({ frame: frame - 4, fps, config: { damping: 16, stiffness: 120 } });
  const level = singerLevelAt(t);
  const downFrame = toFrame(DOWN[0]);
  const makeFrame = toFrame(MAKE_TIME);
  const flipFrames = THEME_TIMES.slice(1).map(toFrame);
  // A small kick on each flip: caption punch and a brief flash.
  const kick = flipFrames.reduce((acc, f) => acc + interpolate(frame - f, [0, 2, 9], [0, 1, 0], clamp), 0);
  const drift = interpolate(frame, [0, makeFrame, total], [1, 1.04, 1.1], clamp);

  return (
    <ThemeContext.Provider value={themeAt(t)}>
      <AbsoluteFill style={{ overflow: "hidden" }}>
        <Backdrop />
        <AbsoluteFill style={{ transform: `scale(${drift})`, transformOrigin: "760px 560px" }}>
          <Tv y={240 + (1 - tvIn) * 200} opacity={tvIn} flash={level * 0.6 + kick * 0.5}>
            <LyricsScreen songStart={songStart} />
          </Tv>
          <Phone x={1440 + (1 - phoneIn) * 400} y={250} opacity={phoneIn} glow={level * 0.6 + kick * 0.4}>
            <ControlsScreen songStart={songStart} />
          </Phone>
        </AbsoluteFill>
        <Caption start={2} end={downFrame - 4}>
          NEED A <Accent>HAND?</Accent>
        </Caption>
        <Caption start={downFrame} end={makeFrame - 2}>
          OR SING IT <Accent>SOLO.</Accent>
        </Caption>
        <Caption start={makeFrame} end={total + 10} punch={kick}>
          MAKE IT <Accent>YOURS.</Accent>
        </Caption>
        <AbsoluteFill style={{ background: "#fff", opacity: kick * 0.18, pointerEvents: "none" }} />
        <Overlay />
      </AbsoluteFill>
    </ThemeContext.Provider>
  );
};
