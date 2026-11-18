import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, random, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Backdrop, Overlay } from "../components/Backdrop";
import { Cover, TV_H, TV_W, Tv } from "../components/Devices";
import { color, font } from "../theme";

/**
 * The opening: "KARAOKE NIGHT." → "ANY SONG." over a rushing wall of covers →
 * "YOUR TV." as the TV arrives and lights up with the logo → the camera
 * pushes through the screen into the dark, where the remote shot begins.
 */
export const HOOK_SHOT_FRAMES = 210;

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

const NIGHT_IN = 4;
const SONG_IN = 40;
const TV_IN = 92;
const LOGO_IN = 122;
const PUSH_START = 172;

const Slam: React.FC<{ text: string; start: number; end: number; accent?: boolean; y?: number }> = ({
  text,
  start,
  end,
  accent,
  y = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (frame < start || frame >= end) return null;
  const s = spring({ frame: frame - start, fps, config: { damping: 11, stiffness: 200 } });
  const out = interpolate(frame, [end - 6, end], [1, 0], clamp);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", transform: `translateY(${y}px)` }}>
      <div
        style={{
          fontFamily: font.display,
          fontSize: 150,
          color: accent ? color.magenta : color.ink,
          textShadow: accent ? "0 0 50px rgba(255,42,109,0.65)" : "0 0 40px rgba(0,0,0,0.8)",
          opacity: s * out,
          transform: `scale(${1.5 - s * 0.5})`,
          letterSpacing: 2,
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};

/** Rows of covers streaming sideways, alternating direction: "any song". */
const CoverWall: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame - SONG_IN;
  if (t < -2 || frame >= TV_IN + 6) return null;
  const opacity = interpolate(frame, [SONG_IN - 2, SONG_IN + 6, TV_IN - 4, TV_IN + 6], [0, 0.4, 0.4, 0], clamp);
  const rows = 6;
  const size = 170;
  const gap = 22;
  return (
    <AbsoluteFill style={{ opacity, transform: "rotate(-8deg) scale(1.25)" }}>
      {Array.from({ length: rows }).map((_, r) => {
        const dir = r % 2 === 0 ? -1 : 1;
        const speed = 16 + random(`speed-${r}`) * 10;
        const offset = dir * t * speed - 400;
        return (
          <div
            key={r}
            style={{
              position: "absolute",
              top: -60 + r * (size + gap),
              left: offset % ((size + gap) * 4) - (size + gap) * 4,
              display: "flex",
              gap,
            }}
          >
            {Array.from({ length: 22 }).map((__, c) => {
              // Magenta through violet to orange: the theme's warm half, not a rainbow.
              const h = (250 + Math.floor(random(`h-${r}-${c}`) * 150)) % 360;
              return <Cover key={c} hues={[h, (h + 30 + random(`d-${r}-${c}`) * 40) % 360]} size={size} radius={8} />;
            })}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

const LogoScreen: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const on = interpolate(frame, [LOGO_IN - 4, LOGO_IN + 2], [0, 1], clamp);
  const bunny = spring({ frame: frame - LOGO_IN, fps, config: { damping: 10, stiffness: 160 } });
  const word = spring({ frame: frame - LOGO_IN - 8, fps, config: { damping: 14 } });
  const tag = spring({ frame: frame - LOGO_IN - 18, fps, config: { damping: 16 } });
  return (
    <AbsoluteFill style={{ background: color.void, alignItems: "center", justifyContent: "center" }}>
      <AbsoluteFill
        style={{
          opacity: on,
          background: "radial-gradient(ellipse at 50% 60%, rgba(122,4,235,0.55), transparent 65%)",
        }}
      />
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", opacity: on }}>
        <Img
          src={staticFile("bunny.png")}
          style={{ width: 230, height: 230, transform: `scale(${bunny}) rotate(${(1 - bunny) * -12}deg)` }}
        />
        <div
          style={{
            marginTop: 8,
            fontFamily: font.display,
            fontSize: 58,
            color: color.magenta,
            textShadow: "0 0 30px rgba(255,42,109,0.6)",
            opacity: word,
            transform: `translateY(${(1 - word) * 24}px)`,
            letterSpacing: 2,
          }}
        >
          OPEN KARAOKE STUDIO
        </div>
        <div
          style={{
            marginTop: 10,
            fontFamily: font.body,
            fontWeight: 500,
            fontSize: 30,
            color: color.dim,
            opacity: tag,
          }}
        >
          Karaoke for a night in with friends.
        </div>
      </div>
      <AbsoluteFill
        style={{
          backgroundImage: "repeating-linear-gradient(to bottom, rgba(255,255,255,0.035) 0 1px, transparent 1px 3px)",
        }}
      />
    </AbsoluteFill>
  );
};

export const HookShot: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tvIn = spring({ frame: frame - TV_IN, fps, config: { damping: 15, stiffness: 120 } });
  // Push through the TV screen: scale around the screen's centre until it fills the frame and beyond.
  const push = interpolate(frame, [PUSH_START, HOOK_SHOT_FRAMES], [0, 1], {
    ...clamp,
    easing: Easing.in(Easing.cubic),
  });
  const tvScale = (0.55 + tvIn * 0.25) * (1 + push * 5);
  const tvTop = (1080 - TV_H) / 2 - 20;
  const caption = interpolate(frame, [TV_IN + 4, TV_IN + 12, LOGO_IN + 26, LOGO_IN + 36], [0, 1, 1, 0], clamp);
  const darkOut = interpolate(frame, [HOOK_SHOT_FRAMES - 10, HOOK_SHOT_FRAMES], [0, 1], clamp);

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <Backdrop />
      <CoverWall />
      {frame >= SONG_IN && frame < TV_IN && (
        <AbsoluteFill
          style={{ background: "radial-gradient(ellipse 55% 35% at center, rgba(7,6,13,0.92), rgba(7,6,13,0.2) 80%)" }}
        />
      )}
      <Slam text="KARAOKE NIGHT." start={NIGHT_IN} end={SONG_IN} />
      <Slam text="ANY SONG." start={SONG_IN} end={TV_IN} accent />
      {frame >= TV_IN && (
        <AbsoluteFill
          style={{
            opacity: tvIn,
            transform: `scale(${tvScale})`,
            transformOrigin: `960px ${tvTop + TV_H / 2}px`,
          }}
        >
          {/* Tv renders at TV_X; shift it so it's centred in the frame. */}
          <div style={{ position: "absolute", left: (1920 - TV_W) / 2 - 150, top: 0 }}>
            <Tv y={tvTop} flash={interpolate(frame, [LOGO_IN, LOGO_IN + 4, LOGO_IN + 30], [0, 1, 0.2], clamp)}>
              <LogoScreen />
            </Tv>
          </div>
        </AbsoluteFill>
      )}
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: 70, opacity: caption }}>
        <div
          style={{
            fontFamily: font.display,
            fontSize: 84,
            color: color.ink,
            transform: `scale(${1.1 - caption * 0.1})`,
          }}
        >
          YOUR <span style={{ color: color.magenta, textShadow: "0 0 40px rgba(255,42,109,0.6)" }}>TV.</span>
        </div>
      </AbsoluteFill>
      <AbsoluteFill style={{ background: color.void, opacity: darkOut }} />
      <Overlay />
    </AbsoluteFill>
  );
};
