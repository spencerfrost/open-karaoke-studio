import React from "react";
import { Composition } from "remotion";
import { evenBeats } from "./beats";
import { OPEN_BACKGROUNDS } from "./components/CoverBackgrounds";
import { FPS, OPEN_PREVIEW_FRAMES, SHOWCASE_FRAMES, Showcase } from "./Showcase";
import { CLOSE_SHOT_BEATS, CloseShot } from "./shots/CloseShot";
import { FIND_SHOT_BEATS, FindShot } from "./shots/FindShot";
import { OPEN_SHOT_BEATS, OpenShot, TV_SHOT_BEATS, TvShot } from "./shots/HookShot";
import { REMOTE_SHOT_BEATS, RemoteShot } from "./shots/RemoteShot";
import { SingShot, singShotFrames } from "./shots/SingShot";
import { SPLIT_SHOT_BEATS, SplitShot } from "./shots/SplitShot";

const SIZE = { fps: FPS, width: 1920, height: 1080 } as const;
/** A shot rendered on its own runs on evenly spaced beats at the song's tempo. */
const beatsLong = (n: number) => evenBeats(FPS)[n];

export const Root: React.FC = () => (
  <>
    <Composition id="Showcase" component={Showcase} durationInFrames={SHOWCASE_FRAMES} {...SIZE} />
    <Composition id="OpenShot" component={OpenShot} durationInFrames={beatsLong(OPEN_SHOT_BEATS)} {...SIZE} />
    <Composition id="FindShot" component={FindShot} durationInFrames={beatsLong(FIND_SHOT_BEATS)} {...SIZE} />
    <Composition id="TvShot" component={TvShot} durationInFrames={beatsLong(TV_SHOT_BEATS)} {...SIZE} />
    <Composition id="RemoteShot" component={RemoteShot} durationInFrames={beatsLong(REMOTE_SHOT_BEATS)} {...SIZE} />
    <Composition id="SplitShot" component={SplitShot} durationInFrames={beatsLong(SPLIT_SHOT_BEATS)} {...SIZE} />
    <Composition
      id="SingShot"
      component={SingShot}
      durationInFrames={singShotFrames(35.67, FPS)}
      defaultProps={{ songStart: 35.67 }}
      {...SIZE}
    />
    {/* The open with each background option, on the real soundtrack and beats, into the start of FIND. */}
    {OPEN_BACKGROUNDS.map((background) => (
      <Composition
        key={background}
        id={`Open-${background}`}
        component={Showcase}
        durationInFrames={OPEN_PREVIEW_FRAMES}
        defaultProps={{ openBackground: background }}
        {...SIZE}
      />
    ))}
    <Composition id="CloseShot" component={CloseShot} durationInFrames={beatsLong(CLOSE_SHOT_BEATS)} {...SIZE} />
  </>
);
