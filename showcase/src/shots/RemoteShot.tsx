import React from "react";
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Phone, PHONE_BEZEL, TV_BEZEL, TV_X, TV_Y, Tv } from "../components/Devices";
import { Backdrop, Overlay } from "../components/Backdrop";
import { Point, Pulse } from "../components/Pulse";
import {
  GUEST_TAP_POINT,
  GuestPhoneScreen,
  MAIN_TAP_POINT,
  MainPhoneScreen,
  TvQueueScreen,
  tvRowTarget,
} from "../components/Screens";
import { BeatFrames, evenBeats } from "../beats";
import { QUEUE } from "../songs";
import { color, font } from "../theme";

/**
 * "Everyone's phone is the remote."
 *
 * One phone searches and adds a song; it flies to the TV and lands in the
 * queue. The camera pulls back to reveal four more phones, and each sends its
 * song in turn, stacking up the rotation.
 */
/** Shot length in beats; every cut, tap and landing sits on a beat. */
export const REMOTE_SHOT_BEATS = 20;

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/** The shot's timeline, in frames, from its beats. */
const timeline = (B: BeatFrames) => {
  /** The frame halfway through beat n. */
  const half = (n: number) => Math.round((B[n] + B[n + 1]) / 2);
  return {
  line1: B[0],
  line2: B[1],
  // The headline snaps up out of the way just before the devices pop in.
  rise: [B[3] - 9, B[3] - 1],
  devicesIn: B[3],
  // Typing starts as soon as the phone has landed.
  typeStart: B[3] + 6,
  mainTap: B[7],
  // The first song lands on the TV; a beat later the camera snaps back.
  mainLand: B[9],
  zoom: [B[10], B[10] + 10],
  // Rapid fire: a guest taps every half beat; each song lands a beat later.
  guestTaps: [B[11], half(11), B[12], half(12)],
  guestLands: [B[12], half(12), B[13], half(13)],
  outro: B[16],
  outroLine2: B[17],
  end: B[REMOTE_SHOT_BEATS],
  };
};
type Timeline = ReturnType<typeof timeline>;

const MAIN_PHONE = { x: 1440, y: 210 };
const GUEST_SCALE = 0.62;
/** Guest phones sit outside the first frame; the pull-back reveals them. */
const GUESTS = [
  { x: -360, y: -110, fromX: -900, fromY: -110 },
  { x: 1840, y: 760, fromX: 2500, fromY: 760 },
  { x: -360, y: 650, fromX: -900, fromY: 650 },
  { x: 1840, y: -200, fromX: 2500, fromY: -200 },
];

const tvPoint = (row: number): Point => {
  const t = tvRowTarget(row);
  return { x: TV_X + TV_BEZEL + t.x, y: TV_Y + TV_BEZEL + t.y };
};

const Headline: React.FC<{ T: Timeline }> = ({ T }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const line1 = spring({ frame: frame - T.line1, fps, config: { damping: 12, stiffness: 180 } });
  const line2 = spring({ frame: frame - T.line2, fps, config: { damping: 12, stiffness: 180 } });
  const rise = interpolate(frame, T.rise, [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  const fade = interpolate(frame, [T.zoom[0], T.zoom[0] + 6], [1, 0], clamp);
  return (
    <AbsoluteFill
      style={{
        alignItems: "center",
        justifyContent: "center",
        opacity: fade,
        transform: `translateY(${rise * -430}px) scale(${1 - rise * 0.5})`,
      }}
    >
      <div style={{ textAlign: "center", fontFamily: font.display, lineHeight: 1.05 }}>
        <div
          style={{
            fontSize: 112,
            color: color.ink,
            opacity: line1,
            transform: `translateY(${(1 - line1) * 60}px) scale(${1.2 - line1 * 0.2})`,
          }}
        >
          EVERYONE'S PHONE
        </div>
        <div
          style={{
            fontSize: 112,
            color: color.magenta,
            opacity: line2,
            transform: `translateY(${(1 - line2) * 60}px) scale(${1.2 - line2 * 0.2})`,
            textShadow: "0 0 40px rgba(255,42,109,0.6)",
          }}
        >
          IS THE REMOTE.
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Outro: React.FC<{ T: Timeline }> = ({ T }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const dim = interpolate(frame, [T.outro, T.outro + 14], [0, 0.6], clamp);
  const a = spring({ frame: frame - T.outro, fps, config: { damping: 12, stiffness: 170 } });
  const b = spring({ frame: frame - T.outroLine2, fps, config: { damping: 14 } });
  if (frame < T.outro) return null;
  return (
    <AbsoluteFill style={{ background: `rgba(7,6,13,${dim})`, alignItems: "center", justifyContent: "center" }}>
      <div style={{ textAlign: "center" }}>
        <div
          style={{
            fontFamily: font.display,
            fontSize: 104,
            color: color.ink,
            opacity: a,
            transform: `scale(${1.25 - a * 0.25})`,
          }}
        >
          FIVE PHONES. <span style={{ color: color.magenta, textShadow: "0 0 40px rgba(255,42,109,0.6)" }}>ONE TV.</span>
        </div>
        <div
          style={{
            marginTop: 18,
            fontFamily: font.body,
            fontWeight: 500,
            fontSize: 46,
            color: color.dim,
            opacity: b,
            transform: `translateY(${(1 - b) * 30}px)`,
          }}
        >
          No app to download. Just the code on the TV.
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const RemoteShot: React.FC<{ beats?: BeatFrames }> = ({ beats = evenBeats() }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const T = timeline(beats);
  const landFrames = [T.mainLand, ...T.guestLands];

  const devicesIn = spring({ frame: frame - T.devicesIn, fps, config: { damping: 14, stiffness: 220 } });
  const phoneIn = spring({ frame: frame - T.devicesIn - 3, fps, config: { damping: 14, stiffness: 220 } });
  // A quick snap back rather than a glide: fast in the middle, settling at the end.
  const zoom = interpolate(frame, T.zoom, [0, 1], { ...clamp, easing: Easing.bezier(0.6, 0, 0.15, 1) });
  // A slow drift in, then the pull-back, then a slow drift through the outro.
  const drift = interpolate(frame, [T.devicesIn, T.zoom[0]], [1.0, 1.04], clamp);
  const settle = interpolate(frame, [T.zoom[1], T.end], [0, 0.03], clamp);
  const camScale = drift * (1 - zoom * 0.3) + settle;
  const outroBlur = interpolate(frame, [T.outro, T.outro + 16], [0, 10], clamp);
  const camX = zoom * 20;

  const tvFlash = landFrames.reduce(
    (acc, f) => acc + interpolate(frame - f, [0, 3, 20], [0, 1, 0], clamp),
    0,
  );
  const mainGlow = interpolate(frame - T.mainTap, [0, 4, 24], [0, 1, 0], clamp);

  const mainTap: Point = {
    x: MAIN_PHONE.x + PHONE_BEZEL + MAIN_TAP_POINT.x,
    y: MAIN_PHONE.y + PHONE_BEZEL + MAIN_TAP_POINT.y,
  };

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <Backdrop />
      <AbsoluteFill
        style={{
          transform: `translateX(${camX}px) scale(${camScale})`,
          transformOrigin: "960px 540px",
          filter: outroBlur > 0 ? `blur(${outroBlur}px)` : undefined,
        }}
      >
        <Tv y={TV_Y + (1 - devicesIn) * 260} opacity={devicesIn} flash={Math.min(tvFlash, 1)}>
          <TvQueueScreen landFrames={landFrames} />
        </Tv>
        <Phone x={MAIN_PHONE.x + (1 - phoneIn) * 500} y={MAIN_PHONE.y} opacity={phoneIn} glow={mainGlow}>
          <MainPhoneScreen typeStart={T.typeStart} tapFrame={T.mainTap} />
        </Phone>
        {GUESTS.map((g, i) => {
          const enter = spring({ frame: frame - T.zoom[0] - 2 - i * 2, fps, config: { damping: 16, stiffness: 260 } });
          const tap = T.guestTaps[i];
          const glow = interpolate(frame - tap, [0, 4, 24], [0, 1, 0], clamp);
          return (
            <Phone
              key={QUEUE[i + 1].singer}
              x={interpolate(enter, [0, 1], [g.fromX, g.x])}
              y={interpolate(enter, [0, 1], [g.fromY, g.y])}
              scale={GUEST_SCALE}
              opacity={enter}
              glow={glow}
            >
              <GuestPhoneScreen song={QUEUE[i + 1]} tapFrame={tap} />
            </Phone>
          );
        })}
        <Pulse
          from={mainTap}
          to={tvPoint(0)}
          start={T.mainTap + 4}
          duration={T.mainLand - T.mainTap - 4}
          lift={220}
        />
        {GUESTS.map((g, i) => (
          <Pulse
            key={i}
            from={{
              x: g.x + (PHONE_BEZEL + GUEST_TAP_POINT.x) * GUEST_SCALE,
              y: g.y + (PHONE_BEZEL + GUEST_TAP_POINT.y) * GUEST_SCALE,
            }}
            to={tvPoint(i + 1)}
            start={T.guestTaps[i] + 3}
            duration={T.guestLands[i] - T.guestTaps[i] - 3}
            lift={g.y < 0 ? 120 : 200}
          />
        ))}
      </AbsoluteFill>
      <Headline T={T} />
      <Outro T={T} />
      <Overlay />
    </AbsoluteFill>
  );
};
