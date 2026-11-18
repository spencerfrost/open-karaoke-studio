import React from "react";
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Backdrop, Overlay } from "../components/Backdrop";
import waveform from "../data/waveform.json";
import { color, font } from "../theme";

/**
 * "AI takes the song apart." One waveform splits into the singer and the
 * music (real levels from the app's separated tracks of the soundtrack), then
 * the singer row switches off: only the music is playing.
 */
export const SPLIT_SHOT_FRAMES = 150;

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

const SPLIT_START = 38;
const SPLIT_END = 72;
const OFF_START = 100;
const OFF_END = 118;

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

const Label: React.FC<{ text: string; y: number; opacity: number; tone: string }> = ({ text, y, opacity, tone }) => (
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
    }}
  >
    {text}
  </div>
);

export const SplitShot: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const grow = interpolate(frame, [0, 24], [0, 1], clamp);
  const split = interpolate(frame, [SPLIT_START, SPLIT_END], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  const off = interpolate(frame, [OFF_START, OFF_END], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  const playhead = interpolate(frame, [0, SPLIT_SHOT_FRAMES], [0, 1.05], clamp);
  const caption = spring({ frame: frame - 4, fps, config: { damping: 12, stiffness: 180 } });
  const labels = interpolate(frame, [SPLIT_END - 8, SPLIT_END + 4], [0, 1], clamp);
  const singerY = interpolate(split, [0, 1], [580, 430]);
  const musicY = interpolate(split, [0, 1], [580, 780]);

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
        maxH={210}
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
        maxH={210}
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
        opacity={labels * (off > 0.5 ? 0.6 : 1)}
        tone={color.magenta}
      />
      <Label text="MUSIC" y={musicY - 170} opacity={labels} tone="#b07bff" />
      <Overlay />
    </AbsoluteFill>
  );
};
