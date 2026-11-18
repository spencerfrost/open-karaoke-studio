import React from "react";
import { Composition } from "remotion";
import { SHOWCASE_FRAMES, Showcase } from "./Showcase";
import { CLOSE_SHOT_FRAMES, CloseShot } from "./shots/CloseShot";
import { HOOK_SHOT_FRAMES, HookShot } from "./shots/HookShot";
import { REMOTE_SHOT_FRAMES, RemoteShot } from "./shots/RemoteShot";
import { SingShot, singShotFrames } from "./shots/SingShot";
import { SPLIT_SHOT_FRAMES, SplitShot } from "./shots/SplitShot";

export const FPS = 30;

const SIZE = { fps: FPS, width: 1920, height: 1080 } as const;

export const Root: React.FC = () => (
  <>
    <Composition id="Showcase" component={Showcase} durationInFrames={SHOWCASE_FRAMES} {...SIZE} />
    <Composition id="HookShot" component={HookShot} durationInFrames={HOOK_SHOT_FRAMES} {...SIZE} />
    <Composition id="RemoteShot" component={RemoteShot} durationInFrames={REMOTE_SHOT_FRAMES} {...SIZE} />
    <Composition id="SplitShot" component={SplitShot} durationInFrames={SPLIT_SHOT_FRAMES} {...SIZE} />
    <Composition
      id="SingShot"
      component={SingShot}
      durationInFrames={singShotFrames(39.4, FPS)}
      defaultProps={{ songStart: 39.4 }}
      {...SIZE}
    />
    <Composition id="CloseShot" component={CloseShot} durationInFrames={CLOSE_SHOT_FRAMES} {...SIZE} />
  </>
);
