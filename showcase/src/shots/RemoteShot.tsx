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
import { QUEUE } from "../songs";
import { color, font } from "../theme";

/**
 * "Everyone's phone is the remote."
 *
 * One phone searches and adds a song; it flies to the TV and lands in the
 * queue. The camera pulls back to reveal four more phones, and each sends its
 * song in turn, stacking up the rotation.
 */
export const REMOTE_SHOT_FRAMES = 450;

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// Timeline (frames at 30 fps)
const DEVICES_IN = 62;
const TYPE_START = 105;
const MAIN_TAP = 180;
const PULSE_FRAMES = 28;
const ZOOM_START = 226;
const ZOOM_END = 286;
const GUEST_TAP_START = 296;
const GUEST_TAP_STEP = 12;
const OUTRO = 380;

const MAIN_PHONE = { x: 1440, y: 210 };
const GUEST_SCALE = 0.62;
/** Guest phones sit outside the first frame; the pull-back reveals them. */
const GUESTS = [
  { x: -360, y: -110, fromX: -900, fromY: -110 },
  { x: 1840, y: 760, fromX: 2500, fromY: 760 },
  { x: -360, y: 650, fromX: -900, fromY: 650 },
  { x: 1840, y: -200, fromX: 2500, fromY: -200 },
];

const guestTap = (i: number) => GUEST_TAP_START + i * GUEST_TAP_STEP;
const landFrames = [
  MAIN_TAP + 6 + PULSE_FRAMES,
  ...GUESTS.map((_, i) => guestTap(i) + 4 + PULSE_FRAMES),
];

const tvPoint = (row: number): Point => {
  const t = tvRowTarget(row);
  return { x: TV_X + TV_BEZEL + t.x, y: TV_Y + TV_BEZEL + t.y };
};

const Headline: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const line1 = spring({ frame: frame - 4, fps, config: { damping: 12, stiffness: 180 } });
  const line2 = spring({ frame: frame - 18, fps, config: { damping: 12, stiffness: 180 } });
  const rise = interpolate(frame, [56, 86], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  const fade = interpolate(frame, [ZOOM_START, ZOOM_START + 18], [1, 0], clamp);
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

const Outro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const dim = interpolate(frame, [OUTRO, OUTRO + 14], [0, 0.6], clamp);
  const a = spring({ frame: frame - OUTRO - 4, fps, config: { damping: 12, stiffness: 170 } });
  const b = spring({ frame: frame - OUTRO - 22, fps, config: { damping: 14 } });
  if (frame < OUTRO) return null;
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
          Nobody installs anything. They just type the code.
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const RemoteShot: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const devicesIn = spring({ frame: frame - DEVICES_IN, fps, config: { damping: 16, stiffness: 110 } });
  const phoneIn = spring({ frame: frame - DEVICES_IN - 8, fps, config: { damping: 16, stiffness: 110 } });
  const zoom = interpolate(frame, [ZOOM_START, ZOOM_END], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  // A slow drift in, then the pull-back, then a slow drift through the outro.
  const drift = interpolate(frame, [DEVICES_IN, ZOOM_START], [1.0, 1.04], clamp);
  const settle = interpolate(frame, [ZOOM_END, REMOTE_SHOT_FRAMES], [0, 0.03], clamp);
  const camScale = drift * (1 - zoom * 0.3) + settle;
  const outroBlur = interpolate(frame, [OUTRO, OUTRO + 16], [0, 10], clamp);
  const camX = zoom * 20;

  const tvFlash = landFrames.reduce(
    (acc, f) => acc + interpolate(frame - f, [0, 3, 20], [0, 1, 0], clamp),
    0,
  );
  const mainGlow = interpolate(frame - MAIN_TAP, [0, 4, 24], [0, 1, 0], clamp);

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
          <MainPhoneScreen typeStart={TYPE_START} tapFrame={MAIN_TAP} />
        </Phone>
        {GUESTS.map((g, i) => {
          const enter = spring({ frame: frame - ZOOM_START - 14 - i * 6, fps, config: { damping: 15, stiffness: 120 } });
          const tap = guestTap(i);
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
        <Pulse from={mainTap} to={tvPoint(0)} start={MAIN_TAP + 6} duration={PULSE_FRAMES} lift={220} />
        {GUESTS.map((g, i) => (
          <Pulse
            key={i}
            from={{
              x: g.x + (PHONE_BEZEL + GUEST_TAP_POINT.x) * GUEST_SCALE,
              y: g.y + (PHONE_BEZEL + GUEST_TAP_POINT.y) * GUEST_SCALE,
            }}
            to={tvPoint(i + 1)}
            start={guestTap(i) + 4}
            duration={PULSE_FRAMES}
            lift={g.y < 0 ? 120 : 200}
          />
        ))}
      </AbsoluteFill>
      <Headline />
      <Outro />
      <Overlay />
    </AbsoluteFill>
  );
};


