import React from "react";
import { Audio, interpolate, Sequence, staticFile } from "remotion";
import { CLOSE_SHOT_FRAMES, CloseShot } from "./shots/CloseShot";
import { HOOK_SHOT_FRAMES, HookShot } from "./shots/HookShot";
import { REMOTE_SHOT_FRAMES, RemoteShot } from "./shots/RemoteShot";
import { FIRST_WORD_TIME, SingShot, singerLevelAt, singShotFrames } from "./shots/SingShot";
import { SPLIT_SHOT_FRAMES, SplitShot } from "./shots/SplitShot";

const FPS = 30;

// Where each beat starts, in frames.
const HOOK_AT = 0;
const REMOTE_AT = HOOK_AT + HOOK_SHOT_FRAMES;
const SPLIT_AT = REMOTE_AT + REMOTE_SHOT_FRAMES;
const SING_AT = SPLIT_AT + SPLIT_SHOT_FRAMES;

/**
 * The soundtrack starts partway into the song, chosen so the first word on
 * screen ("Get out") is sung the moment the singer fader reaches the top.
 */
const FIRST_WORD = FIRST_WORD_TIME;
const FIRST_WORD_AT = SING_AT + 30;
const SONG_TRIM_FRAMES = Math.round((FIRST_WORD - FIRST_WORD_AT / FPS) * FPS);
/** Song time (seconds) at the start of the sing shot. */
const SING_SONG_START = (SONG_TRIM_FRAMES + SING_AT) / FPS;
/** The sing shot runs on through "MAKE IT YOURS." to a downbeat. */
const SING_FRAMES = singShotFrames(SING_SONG_START, FPS);
const CLOSE_AT = SING_AT + SING_FRAMES;
export const SHOWCASE_FRAMES = CLOSE_AT + CLOSE_SHOT_FRAMES;

const bedVolume = (f: number) =>
  interpolate(f, [0, 12, SHOWCASE_FRAMES - 50, SHOWCASE_FRAMES], [0, 0.9, 0.9, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

export const Showcase: React.FC = () => (
  <>
    <Audio src={staticFile("audio/instrumental.mp3")} trimBefore={SONG_TRIM_FRAMES} volume={bedVolume} />
    <Audio
      src={staticFile("audio/vocals.mp3")}
      trimBefore={SONG_TRIM_FRAMES}
      volume={(f) => singerLevelAt((SONG_TRIM_FRAMES + f) / FPS) * bedVolume(f)}
    />
    <Sequence from={HOOK_AT} durationInFrames={HOOK_SHOT_FRAMES}>
      <HookShot />
    </Sequence>
    <Sequence from={REMOTE_AT} durationInFrames={REMOTE_SHOT_FRAMES}>
      <RemoteShot />
    </Sequence>
    <Sequence from={SPLIT_AT} durationInFrames={SPLIT_SHOT_FRAMES}>
      <SplitShot />
    </Sequence>
    <Sequence from={SING_AT} durationInFrames={SING_FRAMES}>
      <SingShot songStart={SING_SONG_START} />
    </Sequence>
    <Sequence from={CLOSE_AT} durationInFrames={CLOSE_SHOT_FRAMES}>
      <CloseShot />
    </Sequence>
  </>
);
