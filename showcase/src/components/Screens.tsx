import React from "react";
import { Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { QUEUE, QueuedSong } from "../songs";
import { color, font } from "../theme";
import { Cover, PHONE_SCREEN_W, TV_SCREEN_W } from "./Devices";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// ---------------------------------------------------------------------------
// TV: the stage's queue screen
// ---------------------------------------------------------------------------

export const TV_ROW_TOP = 150;
export const TV_ROW_STEP = 86;
export const TV_ROW_H = 78;
export const TV_LIST_X = 40;

/** Screen-space centre of queue row `i`, where a pulse lands. */
export const tvRowTarget = (i: number) => ({
  x: TV_LIST_X + 30,
  y: TV_ROW_TOP + i * TV_ROW_STEP + TV_ROW_H / 2,
});

const ScanTexture: React.FC = () => (
  <div
    style={{
      position: "absolute",
      inset: 0,
      backgroundImage:
        "repeating-linear-gradient(to bottom, rgba(255,255,255,0.035) 0 1px, transparent 1px 3px)",
      pointerEvents: "none",
    }}
  />
);

const QueueRow: React.FC<{ song: QueuedSong; index: number; landFrame: number }> = ({
  song,
  index,
  landFrame,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (frame < landFrame) return null;
  const enter = spring({ frame: frame - landFrame, fps, config: { damping: 14, stiffness: 160 } });
  const flash = interpolate(frame - landFrame, [0, 4, 24], [0, 1, 0], clamp);
  return (
    <div
      style={{
        position: "absolute",
        left: TV_LIST_X,
        top: TV_ROW_TOP + index * TV_ROW_STEP,
        width: 640,
        height: TV_ROW_H,
        display: "flex",
        alignItems: "center",
        gap: 18,
        padding: "0 18px",
        background: index === 0 ? color.raised : color.panel,
        border: `2px solid ${index === 0 ? color.magenta : "rgba(255,255,255,0.06)"}`,
        borderRadius: 4,
        transform: `translateX(${(1 - enter) * 80}px) scale(${0.9 + enter * 0.1})`,
        opacity: enter,
        boxShadow: `0 0 ${10 + flash * 40}px rgba(255,42,109,${flash * 0.8})`,
      }}
    >
      <div
        style={{
          width: 46,
          height: 46,
          borderRadius: 23,
          background: song.avatar,
          color: color.void,
          fontFamily: font.display,
          fontSize: 22,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {song.singer[0]}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontFamily: font.body, fontWeight: 700, fontSize: 26, color: color.ink, lineHeight: 1.05 }}>
          {song.singer}
        </div>
        <div style={{ fontFamily: font.body, fontWeight: 500, fontSize: 20, color: color.dim, lineHeight: 1.1 }}>
          {song.title} · {song.artist}
        </div>
      </div>
      <Cover hues={song.hues} size={54} />
    </div>
  );
};

export const TvQueueScreen: React.FC<{ landFrames: number[] }> = ({ landFrames }) => {
  const frame = useCurrentFrame();
  const emptyOpacity = interpolate(frame, [landFrames[0] - 6, landFrames[0]], [1, 0], clamp);
  const landed = landFrames.filter((f) => frame >= f).length;
  return (
    <div style={{ position: "absolute", inset: 0, background: color.void }}>
      {/* Grid backdrop, like the theme's .theme-pattern */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          opacity: 0.35,
          background:
            "linear-gradient(rgba(122,4,235,0.35) 1px, transparent 1px) 0 0 / 48px 48px, linear-gradient(90deg, rgba(122,4,235,0.35) 1px, transparent 1px) 0 0 / 48px 48px",
        }}
      />
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: "radial-gradient(ellipse at 30% 110%, rgba(122,4,235,0.45), transparent 60%)",
        }}
      />
      {/* Header */}
      <div
        style={{
          position: "absolute",
          left: TV_LIST_X,
          right: 40,
          top: 26,
          display: "flex",
          alignItems: "center",
          gap: 14,
        }}
      >
        <Img src={staticFile("bunny.png")} style={{ width: 52, height: 52 }} />
        <div style={{ fontFamily: font.display, fontSize: 24, color: color.magenta, letterSpacing: 1 }}>
          OPEN KARAOKE STUDIO
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          left: TV_LIST_X,
          top: 106,
          fontFamily: font.mono,
          fontSize: 22,
          letterSpacing: 3,
          color: color.dim,
        }}
      >
        UP NEXT{landed > 0 ? ` · ${landed} ${landed === 1 ? "SINGER" : "SINGERS"}` : ""}
      </div>
      <div
        style={{
          position: "absolute",
          left: TV_LIST_X,
          top: TV_ROW_TOP + 10,
          width: 640,
          opacity: emptyOpacity,
          fontFamily: font.body,
          fontWeight: 500,
          fontSize: 28,
          color: color.faint,
        }}
      >
        Nothing queued yet. Add a song from your phone.
      </div>
      {QUEUE.map((song, i) => (
        <QueueRow key={song.singer} song={song} index={i} landFrame={landFrames[i]} />
      ))}
      {/* Join code */}
      <div
        style={{
          position: "absolute",
          left: 730,
          top: 106,
          width: TV_SCREEN_W - 730 - 40,
          height: 430,
          background: color.panel,
          border: "2px solid rgba(255,255,255,0.08)",
          borderRadius: 4,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 10,
        }}
      >
        <div style={{ fontFamily: font.body, fontWeight: 700, fontSize: 28, color: color.ink }}>
          Want to sing?
        </div>
        <div style={{ fontFamily: font.body, fontWeight: 500, fontSize: 22, color: color.dim }}>
          Type this code on your phone
        </div>
        <div style={{ display: "flex", gap: 10, marginTop: 18 }}>
          {"K7Q2".split("").map((ch) => (
            <div
              key={ch}
              style={{
                width: 64,
                height: 84,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                border: `2px solid ${color.magenta}`,
                background: color.sunk,
                fontFamily: font.display,
                fontSize: 44,
                color: color.ink,
                boxShadow: "0 0 18px rgba(255,42,109,0.35)",
              }}
            >
              {ch}
            </div>
          ))}
        </div>
      </div>
      <ScanTexture />
    </div>
  );
};

// ---------------------------------------------------------------------------
// Phone: the first singer searches and adds a song
// ---------------------------------------------------------------------------

const SEARCH_TEXT = "don't blink";
/** Frames per typed character. */
const TYPE_FRAMES = 3;
export const MAIN_RESULT_TOP = 176;
export const MAIN_RESULT_H = 78;
/** Screen-space centre of the result the first singer taps. */
export const MAIN_TAP_POINT = { x: PHONE_SCREEN_W / 2, y: MAIN_RESULT_TOP + MAIN_RESULT_H / 2 };

const RESULTS: { title: string; artist: string; hues: [number, number] }[] = [
  { title: QUEUE[0].title, artist: QUEUE[0].artist, hues: QUEUE[0].hues },
  { title: "Don't Blink (Extended Mix)", artist: "Dropical", hues: [200, 280] },
  { title: "Blink Twice", artist: "Polar Bloom", hues: [170, 300] },
];

export const MainPhoneScreen: React.FC<{ typeStart: number; tapFrame: number }> = ({ typeStart, tapFrame }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const typed = Math.max(0, Math.min(SEARCH_TEXT.length, Math.floor((frame - typeStart) / TYPE_FRAMES)));
  const typeEnd = typeStart + SEARCH_TEXT.length * TYPE_FRAMES;
  const caretOn = Math.floor(frame / 8) % 2 === 0 || (frame >= typeStart && frame < typeEnd);
  const tapped = frame >= tapFrame;
  const ripple = interpolate(frame - tapFrame, [0, 18], [0, 1], clamp);
  const toast = spring({ frame: frame - tapFrame - 6, fps, config: { damping: 15 } });

  return (
    <div style={{ position: "absolute", inset: 0, background: color.void }}>
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: "radial-gradient(ellipse at 50% 120%, rgba(122,4,235,0.4), transparent 60%)",
        }}
      />
      <div style={{ position: "absolute", left: 20, top: 58, fontFamily: font.display, fontSize: 24, color: color.ink }}>
        Add a song
      </div>
      <div
        style={{
          position: "absolute",
          left: 20,
          right: 20,
          top: 104,
          height: 52,
          border: `2px solid ${frame >= typeStart ? color.magenta : color.faint}`,
          background: color.sunk,
          display: "flex",
          alignItems: "center",
          padding: "0 14px",
          fontFamily: font.body,
          fontWeight: 500,
          fontSize: 20,
          whiteSpace: "nowrap",
          overflow: "hidden",
          color: typed > 0 ? color.ink : color.faint,
          boxShadow: frame >= typeStart ? "0 0 14px rgba(255,42,109,0.35)" : "none",
        }}
      >
        {typed > 0 ? SEARCH_TEXT.slice(0, typed) : "What do you want to sing?"}
        {frame >= typeStart && caretOn && (
          <span style={{ width: 2, height: 26, background: color.ink, marginLeft: 2 }} />
        )}
      </div>
      {RESULTS.map((r, i) => {
        const enter = spring({ frame: frame - typeEnd - 4 - i * 4, fps, config: { damping: 16 } });
        const isTapped = i === 0 && tapped;
        return (
          <div
            key={r.title}
            style={{
              position: "absolute",
              left: 14,
              right: 14,
              top: MAIN_RESULT_TOP + i * (MAIN_RESULT_H + 10),
              height: MAIN_RESULT_H,
              display: "flex",
              alignItems: "center",
              gap: 12,
              padding: "0 10px",
              overflow: "hidden",
              background: isTapped ? color.hover : color.panel,
              border: `2px solid ${isTapped ? color.magenta : "rgba(255,255,255,0.06)"}`,
              opacity: enter,
              transform: `translateY(${(1 - enter) * 30}px)`,
            }}
          >
            <Cover hues={r.hues} size={56} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontFamily: font.body, fontWeight: 700, fontSize: 20, color: color.ink, lineHeight: 1.1 }}>
                {r.title}
              </div>
              <div style={{ fontFamily: font.body, fontWeight: 500, fontSize: 17, color: color.dim }}>{r.artist}</div>
            </div>
            {i === 0 && tapped && (
              <div
                style={{
                  position: "absolute",
                  left: MAIN_TAP_POINT.x - 14 - 60,
                  top: MAIN_RESULT_H / 2 - 60,
                  width: 120,
                  height: 120,
                  borderRadius: 60,
                  background: "rgba(255,42,109,0.45)",
                  transform: `scale(${ripple * 2.4})`,
                  opacity: 1 - ripple,
                }}
              />
            )}
          </div>
        );
      })}
      {/* Toast */}
      <div
        style={{
          position: "absolute",
          left: 20,
          right: 20,
          bottom: 30,
          height: 60,
          background: color.magenta,
          color: color.void,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: font.body,
          fontWeight: 700,
          fontSize: 22,
          opacity: tapped ? toast : 0,
          transform: `translateY(${(1 - toast) * 40}px)`,
        }}
      >
        ✓ You're in the queue
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Phone: another guest with a song ready, pressing "Add to queue"
// ---------------------------------------------------------------------------

export const GUEST_BUTTON_TOP = 528;
export const GUEST_BUTTON_H = 66;
export const GUEST_TAP_POINT = { x: PHONE_SCREEN_W / 2, y: GUEST_BUTTON_TOP + GUEST_BUTTON_H / 2 };

export const GuestPhoneScreen: React.FC<{ song: QueuedSong; tapFrame: number }> = ({ song, tapFrame }) => {
  const frame = useCurrentFrame();
  const pressed = frame >= tapFrame;
  const press = interpolate(frame - tapFrame, [0, 3, 8], [1, 0.92, 1], clamp);
  return (
    <div style={{ position: "absolute", inset: 0, background: color.void }}>
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: `radial-gradient(ellipse at 50% 30%, hsl(${song.hues[0]} 80% 40% / 0.45), transparent 65%)`,
        }}
      />
      <div style={{ position: "absolute", left: 30, top: 90 }}>
        <Cover hues={song.hues} size={250} radius={10} />
      </div>
      <div
        style={{
          position: "absolute",
          left: 30,
          right: 30,
          top: 362,
          fontFamily: font.display,
          fontSize: 24,
          color: color.ink,
          lineHeight: 1.2,
        }}
      >
        {song.title}
      </div>
      <div
        style={{
          position: "absolute",
          left: 30,
          top: 430,
          fontFamily: font.body,
          fontWeight: 500,
          fontSize: 22,
          color: color.dim,
        }}
      >
        {song.artist}
      </div>
      <div
        style={{
          position: "absolute",
          left: 30,
          top: 470,
          fontFamily: font.mono,
          fontSize: 18,
          color: color.faint,
        }}
      >
        SINGING AS {song.singer.toUpperCase()}
      </div>
      <div
        style={{
          position: "absolute",
          left: 30,
          right: 30,
          top: GUEST_BUTTON_TOP,
          height: GUEST_BUTTON_H,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: pressed ? color.success : color.magenta,
          color: color.void,
          fontFamily: font.display,
          fontSize: 22,
          transform: `scale(${press})`,
          boxShadow: `0 0 24px ${pressed ? "rgba(57,255,136,0.5)" : "rgba(255,42,109,0.45)"}`,
        }}
      >
        {pressed ? "✓ QUEUED" : "SING THIS"}
      </div>
    </div>
  );
};
