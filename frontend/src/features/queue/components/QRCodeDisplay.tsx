import React from "react";
import { QRCodeSVG } from "qrcode.react";

interface QRCodeDisplayProps {
  value: string;
  size?: number;
  title?: string;
  description?: string;
  className?: string;
}

const QRCodeDisplay: React.FC<QRCodeDisplayProps> = ({
  value,
  size = 256,
  className = "",
}) => {
  return (
    <div className={`flex flex-col items-center ${className}`}>
      <div
        className="p-4 rounded-lg flex items-center justify-center bg-lemon-chiffon"
        style={{
          boxShadow: `0 0 0 2px #fd9a02, 0 6px 12px rgba(0, 0, 0, 0.3)`,
          width: `${size + 32}px`,
          height: `${size + 32}px`,
        }}
      >
        <QRCodeSVG value={value} size={size} level="M" />
      </div>
    </div>
  );
};

export default QRCodeDisplay;
