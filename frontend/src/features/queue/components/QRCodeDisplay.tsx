import React from "react";
import { QRCodeSVG } from "qrcode.react";

interface QRCodeDisplayProps {
  value: string;
  /** Pixels, or any CSS length (e.g. "9rem") for a code that scales with the page. */
  size?: number | string;
  title?: string;
  description?: string;
  className?: string;
}

const QRCodeDisplay: React.FC<QRCodeDisplayProps> = ({
  value,
  size = 256,
  className = "",
}) => {
  const codeSize = typeof size === "number" ? `${size}px` : size;
  const frameSize = `calc(${codeSize} + 2rem)`;

  return (
    <div className={`flex flex-col items-center ${className}`}>
      <div
        className="p-2 rounded-lg flex items-center justify-center bg-card"
        style={{
          boxShadow:
            "0 0 0 2px var(--primary), 0 6px 12px color-mix(in oklab, var(--overlay) 30%, transparent)",
          width: frameSize,
          height: frameSize,
        }}
      >
        <QRCodeSVG
          value={value}
          level="M"
          style={{ width: codeSize, height: codeSize }}
        />
      </div>
    </div>
  );
};

export default QRCodeDisplay;
