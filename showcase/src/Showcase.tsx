import React from "react";
import { Audio, interpolate, Sequence, staticFile } from "remotion";
import { BEATS, beatFramesFrom, nearestBeat } from "./beats";
import { CLOSE_SHOT_BEATS, CloseShot } from "./shots/CloseShot";
import { FIND_SHOT_BEATS, FindShot } from "./shots/FindShot";
import { OPEN_SHOT_BEATS, OpenShot, TV_SHOT_BEATS, TvShot } from "./shots/HookShot";
import { REMOTE_SHOT_BEATS, RemoteShot } from "./shots/RemoteShot";
import { SING_END_TIME, SingShot, singerLevelAt } from "./shots/SingShot";
import { SPLIT_SHOT_BEATS, SPLIT_STABS, SplitShot, TV_STABS } from "./shots/SplitShot";

export const FPS = 30;

/**
 * The whole video runs on the soundtrack's beat grid. The sing shot starts on
 * the downbeat two bars before "Get out" (the singer comes up in the line
 * before it); the shots before it are counted back from there in beats, so
 * every cut lands on a beat and the video starts on a downbeat. Order follows the app:
 * find a song, the AI splits it, host on the TV, phones queue it, sing.
 */
const SING_BEAT = nearestBeat(40.4) - 8;
const REMOTE_BEAT = SING_BEAT - REMOTE_SHOT_BEATS;
const TV_BEAT = REMOTE_BEAT - TV_SHOT_BEATS;
const SPLIT_BEAT = TV_BEAT - SPLIT_SHOT_BEATS;
const FIND_BEAT = SPLIT_BEAT - FIND_SHOT_BEATS;
const OPEN_BEAT = FIND_BEAT - OPEN_SHOT_BEATS;
const CLOSE_BEAT = nearestBeat(SING_END_TIME);

/** Where in the song the video starts, in frames (the audio's trim). */
const SONG_TRIM_FRAMES = Math.round(BEATS[OPEN_BEAT] * FPS);
const VIDEO_START = SONG_TRIM_FRAMES / FPS;
/** Video frame of a song time. */
const at = (songTime: number) => Math.round((songTime - VIDEO_START) * FPS);
/** Video frame of a song beat. */
const atBeat = (beat: number) => at(BEATS[beat]);

const SHOTS = {
  open: { from: atBeat(OPEN_BEAT), to: atBeat(FIND_BEAT), beat: OPEN_BEAT },
  find: { from: atBeat(FIND_BEAT), to: atBeat(SPLIT_BEAT), beat: FIND_BEAT },
  split: { from: atBeat(SPLIT_BEAT), to: atBeat(TV_BEAT), beat: SPLIT_BEAT },
  tv: { from: atBeat(TV_BEAT), to: atBeat(REMOTE_BEAT), beat: TV_BEAT },
  remote: { from: atBeat(REMOTE_BEAT), to: atBeat(SING_BEAT), beat: REMOTE_BEAT },
  sing: { from: atBeat(SING_BEAT), to: atBeat(CLOSE_BEAT), beat: SING_BEAT },
  close: { from: atBeat(CLOSE_BEAT), to: atBeat(CLOSE_BEAT + CLOSE_SHOT_BEATS), beat: CLOSE_BEAT },
};
export const SHOWCASE_FRAMES = SHOTS.close.to;

/** A shot's beats as frames from its own start. */
const beatsOf = (shot: { from: number; beat: number }) => beatFramesFrom(shot.beat, shot.from, VIDEO_START, FPS);

/** Song time (seconds) at the start of the sing shot, matching the audio. */
const SING_SONG_START = VIDEO_START + SHOTS.sing.from / FPS;

/** The song fades out over the close card's last three beats. */
const FADE_FROM = atBeat(CLOSE_BEAT + CLOSE_SHOT_BEATS - 3);
const bedVolume = (f: number) =>
  interpolate(f, [0, 2, FADE_FROM, SHOWCASE_FRAMES], [0, 0.9, 0.9, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

export const Showcase: React.FC = () => (
  <>
    <Audio src={staticFile("audio/instrumental.mp3")} trimBefore={SONG_TRIM_FRAMES} volume={bedVolume} />
    <Audio
      src={staticFile("audio/vocals.mp3")}
      trimBefore={SONG_TRIM_FRAMES}
      volume={(f) => singerLevelAt(VIDEO_START + f / FPS) * bedVolume(f)}
    />
    <Sequence from={SHOTS.open.from} durationInFrames={SHOTS.open.to - SHOTS.open.from}>
      <OpenShot beats={beatsOf(SHOTS.open)} />
    </Sequence>
    <Sequence from={SHOTS.find.from} durationInFrames={SHOTS.find.to - SHOTS.find.from}>
      <FindShot beats={beatsOf(SHOTS.find)} />
    </Sequence>
    <Sequence from={SHOTS.split.from} durationInFrames={SHOTS.split.to - SHOTS.split.from}>
      <SplitShot beats={beatsOf(SHOTS.split)} stabs={SPLIT_STABS.map((t) => at(t) - SHOTS.split.from)} />
    </Sequence>
    <Sequence from={SHOTS.tv.from} durationInFrames={SHOTS.tv.to - SHOTS.tv.from}>
      <TvShot beats={beatsOf(SHOTS.tv)} stabs={TV_STABS.map((t) => at(t) - SHOTS.tv.from)} />
    </Sequence>
    <Sequence from={SHOTS.remote.from} durationInFrames={SHOTS.remote.to - SHOTS.remote.from}>
      <RemoteShot beats={beatsOf(SHOTS.remote)} />
    </Sequence>
    <Sequence from={SHOTS.sing.from} durationInFrames={SHOTS.sing.to - SHOTS.sing.from}>
      <SingShot songStart={SING_SONG_START} />
    </Sequence>
    <Sequence from={SHOTS.close.from} durationInFrames={SHOTS.close.to - SHOTS.close.from}>
      <CloseShot beats={beatsOf(SHOTS.close)} />
    </Sequence>
  </>
);
