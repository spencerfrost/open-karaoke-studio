import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { BeatFrames, evenBeats } from "../beats";
import { Backdrop, Overlay } from "../components/Backdrop";
import { OpenBackground, OpenBackgroundLayer } from "../components/CoverBackgrounds";
import { TV_H, TV_W, Tv } from "../components/Devices";
import { color, font } from "../theme";
import { TV_STABS } from "./SplitShot";

/**
 * The opening and the TV, two blocks that used to be one shot.
 *
 * OpenShot: "KARAOKE NIGHT." → "ANY SONG." over covers (the options for that
 * layer are in components/CoverBackgrounds.tsx).
 * TvShot: "HOSTED ON YOUR TV." slams in and rises to a header; on the
 * song's three chord stabs the TV pops in, its screen powers on with the
 * bunny, and the name lands; then the camera pushes through the screen into
 * the next shot.
 */
export const OPEN_SHOT_BEATS = 6;
export const TV_SHOT_BEATS = 6;

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/** OpenShot's timeline, in frames, from its beats. */
const openTimeline = (B: BeatFrames) => ({ nightIn: B[0], songIn: B[2], end: B[OPEN_SHOT_BEATS] });
type OpenTimeline = ReturnType<typeof openTimeline>;

/** TvShot's timeline, in frames, from its beats and the three stabs. */
const timeline = (B: BeatFrames, [tvIn, screenOn, nameIn]: number[]) => ({
  hostedIn: B[0],
  // The headline is up out of the way just before the TV pops in.
  rise: [tvIn - 9, tvIn - 1],
  tvIn,
  screenOn,
  nameIn,
  pushStart: B[5],
  end: B[TV_SHOT_BEATS],
});
/** Song time the TV shot starts at when rendered on its own. */
const TV_STANDALONE_START = 20.2;
type Timeline = ReturnType<typeof timeline>;

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

/** The TV's screen: dark until the second stab powers it on with the bunny; the name lands on the third. */
const LogoScreen: React.FC<{ T: Timeline }> = ({ T }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  // Power-on: a bright line that opens to the full screen in a few frames.
  const open = interpolate(frame, [T.screenOn - 1, T.screenOn + 3], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  const line = interpolate(frame, [T.screenOn - 1, T.screenOn, T.screenOn + 5], [0, 1, 0], clamp);
  const bunny = spring({ frame: frame - T.screenOn, fps, config: { damping: 9, stiffness: 200 } });
  const word = spring({ frame: frame - T.nameIn, fps, config: { damping: 11, stiffness: 220 } });
  const wordFlash = interpolate(frame, [T.nameIn, T.nameIn + 2, T.nameIn + 10], [0, 1, 0], clamp);
  return (
    <AbsoluteFill style={{ background: color.void, alignItems: "center", justifyContent: "center" }}>
      <AbsoluteFill style={{ transform: `scaleY(${open})`, opacity: open > 0 ? 1 : 0 }}>
        <AbsoluteFill
          style={{ background: "radial-gradient(ellipse at 50% 60%, rgba(122,4,235,0.6), transparent 65%)" }}
        />
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
          <Img
            src={staticFile("bunny.png")}
            style={{
              width: 250,
              height: 250,
              marginTop: -40,
              transform: `scale(${bunny}) rotate(${(1 - bunny) * -14}deg)`,
            }}
          />
          <div
            style={{
              marginTop: 10,
              fontFamily: font.display,
              fontSize: 64,
              color: color.magenta,
              textShadow: `0 0 ${30 + wordFlash * 40}px rgba(255,42,109,${0.6 + wordFlash * 0.4})`,
              opacity: frame >= T.nameIn ? Math.min(1, word * 1.4) : 0,
              transform: `scale(${1.2 - word * 0.2})`,
              letterSpacing: 2,
            }}
          >
            OPEN KARAOKE STUDIO
          </div>
        </AbsoluteFill>
      </AbsoluteFill>
      {/* The power-on line */}
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: line }}>
        <div style={{ width: "100%", height: 6, background: "#fff", boxShadow: "0 0 40px #fff, 0 0 80px rgba(255,42,109,0.9)" }} />
      </AbsoluteFill>
      <AbsoluteFill
        style={{
          backgroundImage: "repeating-linear-gradient(to bottom, rgba(255,255,255,0.035) 0 1px, transparent 1px 3px)",
        }}
      />
    </AbsoluteFill>
  );
};

/** "HOSTED ON YOUR TV.": slams in centred like the others, then rises to a header over the TV. */
const Hosted: React.FC<{ T: Timeline; push: number }> = ({ T, push }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (frame < T.hostedIn) return null;
  const s = spring({ frame: frame - T.hostedIn, fps, config: { damping: 11, stiffness: 200 } });
  const rise = interpolate(frame, T.rise, [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  return (
    <AbsoluteFill
      style={{
        alignItems: "center",
        justifyContent: "center",
        opacity: s * (1 - push * 3),
        transform: `translateY(${rise * -420}px) scale(${(1.25 - s * 0.25) * (1 - rise * 0.38)})`,
      }}
    >
      <div style={{ fontFamily: font.display, fontSize: 120, color: color.ink, letterSpacing: 2, whiteSpace: "nowrap" }}>
        HOSTED ON YOUR{" "}
        <span style={{ color: color.magenta, textShadow: "0 0 50px rgba(255,42,109,0.65)" }}>TV.</span>
      </div>
    </AbsoluteFill>
  );
};

export const OpenShot: React.FC<{ beats?: BeatFrames; background?: OpenBackground }> = ({
  beats = evenBeats(),
  background = "real-wall",
}) => {
  const frame = useCurrentFrame();
  const T = openTimeline(beats);
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <Backdrop />
      <OpenBackgroundLayer kind={background} T={T} beats={beats} />
      {frame >= T.songIn && (
        <AbsoluteFill
          style={{ background: "radial-gradient(ellipse 55% 35% at center, rgba(7,6,13,0.92), rgba(7,6,13,0.2) 80%)" }}
        />
      )}
      <Slam text="KARAOKE NIGHT." start={T.nightIn} end={T.songIn} />
      <Slam text="ANY SONG." start={T.songIn} end={T.end} accent />
      <Overlay />
    </AbsoluteFill>
  );
};

export const TvShot: React.FC<{ beats?: BeatFrames; stabs?: number[] }> = ({ beats = evenBeats(), stabs }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const T = timeline(beats, stabs ?? TV_STABS.map((t) => Math.round((t - TV_STANDALONE_START) * fps)));
  // The TV pops up into place on its beat.
  const tvIn = spring({ frame: frame - T.tvIn, fps, config: { damping: 12, stiffness: 240 } });
  // Push through the TV screen: scale around the screen's centre until it fills the frame and beyond.
  const push = interpolate(frame, [T.pushStart, T.end], [0, 1], {
    ...clamp,
    easing: Easing.in(Easing.cubic),
  });
  const tvScale = 0.9 * (1 + push * 5);
  const tvTop = (1080 - TV_H) / 2 + 30;
  const tvFlash =
    interpolate(frame, [T.screenOn, T.screenOn + 3, T.screenOn + 16], [0, 1, 0.25], clamp) +
    interpolate(frame, [T.nameIn, T.nameIn + 3, T.nameIn + 14], [0, 0.8, 0], clamp);
  const darkOut = interpolate(frame, [T.end - 6, T.end], [0, 1], clamp);

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <Backdrop />
      {frame >= T.tvIn && (
        <AbsoluteFill
          style={{
            opacity: Math.min(1, tvIn * 2),
            transform: `translateY(${(1 - tvIn) * 240}px) scale(${tvScale})`,
            transformOrigin: `960px ${tvTop + TV_H / 2}px`,
          }}
        >
          {/* Tv renders at TV_X; shift it so it's centred in the frame. */}
          <div style={{ position: "absolute", left: (1920 - TV_W) / 2 - 150, top: 0 }}>
            <Tv y={tvTop} flash={Math.min(tvFlash, 1)}>
              <LogoScreen T={T} />
            </Tv>
          </div>
        </AbsoluteFill>
      )}
      <Hosted T={T} push={push} />
      <AbsoluteFill style={{ background: color.void, opacity: darkOut }} />
      <Overlay />
    </AbsoluteFill>
  );
};
