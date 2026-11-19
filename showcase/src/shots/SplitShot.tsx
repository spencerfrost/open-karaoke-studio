import React from "react";
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { BeatFrames, evenBeats } from "../beats";
import { Backdrop, Overlay } from "../components/Backdrop";
import waveform from "../data/waveform.json";
import { color, font } from "../theme";

/**
 * "AI takes the song apart." The song's waveform (built by FIND) tears into
 * the singer and the music on the song's three chord stabs (real levels from
 * the app's separated tracks of the soundtrack), then the singer row switches
 * off on the downbeat after them: only the music is playing.
 */
/** Shot length in beats: two bars. */
export const SPLIT_SHOT_BEATS = 8;

/**
 * The three chord stabs, in song seconds: the onset peaks read off the
 * instrumental, pulled 50 ms earlier so the hits land with the attack.
 */
export const SPLIT_STABS = [16.284, 17.061, 17.491];
/** The same three stabs come back 4.763 s later (two bars on), inside the TV shot. */
export const TV_STABS = SPLIT_STABS.map((t) => t + 4.763);
/** Song time the shot starts at when rendered on its own. */
const STANDALONE_START = 15.49;

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const snap = Easing.bezier(0.6, 0, 0.15, 1);
const normalize = (xs: number[]) => {
  const max = Math.max(...xs);
  return xs.map((x) => x / max);
};
const SINGER = normalize(waveform.vocals);
const MUSIC = normalize(waveform.music);
const MIX = normalize(SINGER.map((v, i) => v * 0.6 + MUSIC[i]));

const WIDTH = 1440;
const BAR_GAP = 5;
const BAR_W = WIDTH / SINGER.length - BAR_GAP;
const WAVE_Y = 580;
const MAX_H = 210;

/** Where the unsplit waveform's bars sit, so FIND can build exactly this. */
export const WAVE = {
  left: (1920 - WIDTH) / 2,
  y: WAVE_Y,
  barW: BAR_W,
  gap: BAR_GAP,
  maxH: MAX_H,
  levels: MIX,
};

const Row: React.FC<{
  own: number[];
  split: number;
  y: number;
  maxH: number;
  fill: string;
  glow: string;
  opacity: number;
  flatten: number;
  playhead: number;
  grow: number;
}> = ({ own, split, y, maxH, fill, glow, opacity, flatten, playhead, grow }) => {
  const frame = useCurrentFrame();
  return (
    <div style={{ position: "absolute", left: (1920 - WIDTH) / 2, top: y, width: WIDTH, height: 0, opacity }}>
      {own.map((v, i) => {
        const level = MIX[i] + (v - MIX[i]) * split;
        const shimmer = 1 + Math.sin(frame / 3 + i * 0.7) * 0.06;
        const h = Math.max(6, level * maxH * shimmer * (1 - flatten * 0.88) * Math.min(1, Math.max(0, grow * 1.6 - i / own.length)));
        const lit = i / own.length < playhead;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: i * (BAR_W + BAR_GAP),
              top: -h / 2,
              width: BAR_W,
              height: h,
              borderRadius: BAR_W / 2,
              background: fill,
              opacity: lit ? 1 : 0.55,
              boxShadow: lit ? `0 0 14px ${glow}` : "none",
            }}
          />
        );
      })}
    </div>
  );
};

const Label: React.FC<{ text: string; y: number; opacity: number; tone: string; pop: number }> = ({
  text,
  y,
  opacity,
  tone,
  pop,
}) => (
  <div
    style={{
      position: "absolute",
      left: (1920 - WIDTH) / 2,
      top: y,
      fontFamily: font.mono,
      fontSize: 34,
      letterSpacing: 6,
      color: tone,
      opacity,
      transform: `translateX(${(1 - pop) * -30}px)`,
    }}
  >
    {text}
  </div>
);

export const SplitShot: React.FC<{ beats?: BeatFrames; stabs?: number[] }> = ({ beats = evenBeats(), stabs }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const [tear, singerIn, musicIn] = stabs ?? SPLIT_STABS.map((t) => Math.round((t - STANDALONE_START) * fps));
  // The singer switches off on the downbeat after the stabs.
  const OFF_START = beats[6];
  const END = beats[SPLIT_SHOT_BEATS];
  const grow = 1;
  const split = interpolate(frame, [tear, tear + 7], [0, 1], { ...clamp, easing: snap });
  const off = interpolate(frame, [OFF_START, OFF_START + 6], [0, 1], { ...clamp, easing: snap });
  const playhead = interpolate(frame, [0, END], [0, 1.05], clamp);
  const caption = spring({ frame, fps, config: { damping: 12, stiffness: 180 } });
  const singerLabel = spring({ frame: frame - singerIn, fps, config: { damping: 12, stiffness: 220 } });
  const musicLabel = spring({ frame: frame - musicIn, fps, config: { damping: 12, stiffness: 220 } });
  const singerY = interpolate(split, [0, 1], [WAVE_Y, 430]);
  const musicY = interpolate(split, [0, 1], [WAVE_Y, 780]);

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <Backdrop />
      <AbsoluteFill style={{ alignItems: "center", paddingTop: 90 }}>
        <div
          style={{
            fontFamily: font.display,
            fontSize: 92,
            color: color.ink,
            opacity: caption,
            transform: `scale(${1.3 - caption * 0.3})`,
          }}
        >
          AI TAKES THE SONG <span style={{ color: color.magenta, textShadow: "0 0 40px rgba(255,42,109,0.6)" }}>APART.</span>
        </div>
      </AbsoluteFill>
      <Row
        own={MUSIC}
        split={split}
        y={musicY}
        maxH={MAX_H}
        fill={`linear-gradient(to bottom, #b07bff, ${color.violet})`}
        glow="rgba(122,4,235,0.8)"
        opacity={1}
        flatten={0}
        playhead={playhead}
        grow={grow}
      />
      <Row
        own={SINGER}
        split={split}
        y={singerY}
        maxH={MAX_H}
        fill={`linear-gradient(to bottom, #ff6b97, ${color.magenta})`}
        glow="rgba(255,42,109,0.8)"
        opacity={(split > 0 ? 1 : 0.5) * (1 - off * 0.7)}
        flatten={off}
        playhead={playhead}
        grow={grow}
      />
      <Label
        text={off > 0.5 ? "SINGER · OFF" : "SINGER"}
        y={singerY - 170}
        opacity={(frame >= singerIn ? singerLabel : 0) * (off > 0.5 ? 0.6 : 1)}
        tone={color.magenta}
        pop={singerLabel}
      />
      <Label text="MUSIC" y={musicY - 170} opacity={frame >= musicIn ? musicLabel : 0} tone="#b07bff" pop={musicLabel} />
      <Overlay />
    </AbsoluteFill>
  );
};
