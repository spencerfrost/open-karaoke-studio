import React from "react";
import { useTheme } from "../themes";

export const PHONE_W = 330;
export const PHONE_H = 680;
export const PHONE_BEZEL = 10;
/** The phone screen's size; screen content is laid out in these units. */
export const PHONE_SCREEN_W = PHONE_W - PHONE_BEZEL * 2;
export const PHONE_SCREEN_H = PHONE_H - PHONE_BEZEL * 2;

interface PhoneProps {
  x: number;
  y: number;
  scale?: number;
  opacity?: number;
  glow?: number;
  children: React.ReactNode;
}

/** A plain phone frame at stage coordinates (x, y are the top-left corner). */
export const Phone: React.FC<PhoneProps> = ({ x, y, scale = 1, opacity = 1, glow = 0, children }) => {
  const theme = useTheme();
  return (
  <div
    style={{
      position: "absolute",
      left: x,
      top: y,
      width: PHONE_W,
      height: PHONE_H,
      transform: `scale(${scale})`,
      transformOrigin: "top left",
      opacity,
      borderRadius: 52,
      background: "#15131c",
      padding: PHONE_BEZEL,
      boxShadow: [
        "0 0 0 2px #2a2733",
        "0 40px 80px rgba(0,0,0,0.6)",
        `0 0 ${40 + glow * 60}px rgba(${theme.primaryRgb},${0.12 + glow * 0.5})`,
      ].join(", "),
    }}
  >
    <div
      style={{
        position: "relative",
        width: PHONE_SCREEN_W,
        height: PHONE_SCREEN_H,
        borderRadius: 42,
        overflow: "hidden",
        background: theme.page,
      }}
    >
      {children}
      {/* Dynamic island */}
      <div
        style={{
          position: "absolute",
          top: 12,
          left: PHONE_SCREEN_W / 2 - 50,
          width: 100,
          height: 28,
          borderRadius: 14,
          background: "#000",
        }}
      />
    </div>
  </div>
  );
};

export const TV_X = 150;
export const TV_Y = 270;
export const TV_W = 1130;
export const TV_H = 636;
export const TV_BEZEL = 14;
export const TV_SCREEN_W = TV_W - TV_BEZEL * 2;
export const TV_SCREEN_H = TV_H - TV_BEZEL * 2;

interface TvProps {
  y?: number;
  opacity?: number;
  flash?: number;
  children: React.ReactNode;
}

/** A plain TV frame with a stand, at the fixed TV position. */
export const Tv: React.FC<TvProps> = ({ y = TV_Y, opacity = 1, flash = 0, children }) => {
  const theme = useTheme();
  return (
  <div style={{ position: "absolute", left: TV_X, top: y, width: TV_W, opacity }}>
    <div
      style={{
        width: TV_W,
        height: TV_H,
        padding: TV_BEZEL,
        borderRadius: 18,
        background: "#0c0b10",
        boxShadow: [
          "0 0 0 2px #24222c",
          "0 50px 100px rgba(0,0,0,0.65)",
          `0 0 ${120 + flash * 80}px rgba(${theme.haloRgb},${0.25 + flash * 0.35})`,
        ].join(", "),
      }}
    >
      <div
        style={{
          position: "relative",
          width: TV_SCREEN_W,
          height: TV_SCREEN_H,
          borderRadius: 6,
          overflow: "hidden",
          background: theme.page,
        }}
      >
        {children}
      </div>
    </div>
    {/* Stand */}
    <div style={{ margin: "0 auto", width: 120, height: 28, background: "#16141d" }} />
    <div style={{ margin: "0 auto", width: 360, height: 10, borderRadius: 5, background: "#1d1a26" }} />
  </div>
  );
};

/** A song cover stand-in: a gradient square. */
export const Cover: React.FC<{ hues: [number, number]; size: number; radius?: number }> = ({
  hues,
  size,
  radius = 6,
}) => (
  <div
    style={{
      width: size,
      height: size,
      flexShrink: 0,
      borderRadius: radius,
      background: `linear-gradient(135deg, hsl(${hues[0]} 90% 58%), hsl(${hues[1]} 85% 32%))`,
      boxShadow: "inset 0 0 0 1px rgba(255,255,255,0.12)",
    }}
  />
);
