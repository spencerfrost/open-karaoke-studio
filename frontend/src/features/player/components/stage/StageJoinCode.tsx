/**
 * StageJoinCode - the join code and QR at the foot of the right rail.
 *
 * It lives outside the rail's collapsible content because it has to stay on
 * screen the whole song: someone who walks in mid-song should be able to scan
 * in without waiting for the host to wiggle the mouse. So when the rails
 * collapse it is the one thing that doesn't hide or dim. The card around it
 * fades away, the label folds up, and the code shrinks to fit the collapsed
 * rail. It is one element the whole time, so it shrinks and slides into
 * place instead of swapping for a copy.
 */

import React from "react";
import { QRCodeSVG } from "qrcode.react";
import { useSessionStore } from "@/stores/sessionStore";
import { cn } from "@/lib/utils";

const QR_OPEN = "9.5rem";

interface StageJoinCodeProps {
  collapsed: boolean;
  /** QR size while collapsed. May exceed the rail's width; it overflows centred. */
  collapsedSize: string;
  /** Space kept under the code while collapsed, so the ambient bar can't cover it. */
  collapsedInset: string;
}

const StageJoinCode: React.FC<StageJoinCodeProps> = ({
  collapsed,
  collapsedSize,
  collapsedInset,
}) => {
  const { displayCode } = useSessionStore();
  if (!displayCode) return null;

  const qrSize = collapsed ? collapsedSize : QR_OPEN;

  return (
    <div
      className={cn(
        "flex shrink-0 flex-col items-center rounded-md border transition-[background-color,border-color,padding] duration-500 motion-reduce:transition-none",
        collapsed
          ? "border-transparent bg-transparent p-0"
          : "border-glass-border/10 bg-glass/5 px-2 pt-2 pb-4",
      )}
      style={{ marginBottom: collapsed ? collapsedInset : 0 }}
    >
      {/* 1fr -> 0fr folds the label's height away with its opacity. */}
      <div
        className={cn(
          "grid transition-[grid-template-rows,opacity] duration-500 motion-reduce:transition-none",
          collapsed && "opacity-0",
        )}
        style={{ gridTemplateRows: collapsed ? "0fr" : "1fr" }}
        aria-hidden={collapsed}
      >
        <div className="min-h-0 overflow-hidden">
          <div className="flex items-center gap-2 pb-4">
            <span className="text-base uppercase tracking-[0.08em] text-foreground/60">
              Join Code:
            </span>
            <span className="font-accent text-3xl leading-tight text-primary">
              {displayCode}
            </span>
          </div>
        </div>
      </div>

      {/* No frame: the code's own one-module white margin is the quiet zone
          a scanner needs, and nothing else around it is required. */}
      <QRCodeSVG
        value={`${window.location.origin}/join/${displayCode}`}
        level="M"
        marginSize={1}
        title={`Scan to join session ${displayCode}`}
        className="rounded-sm shadow-lg transition-[width,height] duration-500 motion-reduce:transition-none"
        style={{ width: qrSize, height: qrSize }}
      />
    </div>
  );
};

export default StageJoinCode;
