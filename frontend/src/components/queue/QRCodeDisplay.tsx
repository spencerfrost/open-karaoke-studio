import React, { useEffect, useState } from 'react';
import { QrCode } from 'lucide-react';
import vintageTheme from '../../utils/theme';

interface QRCodeDisplayProps {
  value: string;
  size?: number;
  title?: string;
  description?: string;
  className?: string;
}

const QRCodeDisplay: React.FC<QRCodeDisplayProps> = ({
  value,
  size = 200,
  title = 'Scan to Add Songs',
  description = 'Use your phone to add songs to the queue',
  className = '',
}) => {
  const colors = vintageTheme.colors;
  const [qrCodeUrl, setQrCodeUrl] = useState('');
  
  // Generate QR code URL when component mounts or value changes
  useEffect(() => {
    // Using Google Charts API to generate QR code
    // In a production app, you might want to use a dedicated QR code library
    const encodedValue = encodeURIComponent(value);
    const url = `https://chart.googleapis.com/chart?cht=qr&chl=${encodedValue}&chs=${size}x${size}&chco=000000`;
    setQrCodeUrl(url);
  }, [value, size]);
  
  return (
    <div className={`flex flex-col items-center ${className}`}>
      {title && (
        <h2 
          className="text-2xl font-semibold text-center mb-2"
          style={{ color: colors.orangePeel }}
        >
          {title}
        </h2>
      )}
      
      {description && (
        <p 
          className="text-center mb-6 opacity-80"
          style={{ color: colors.lemonChiffon }}
        >
          {description}
        </p>
      )}
      
      <div 
        className="p-4 rounded-lg flex items-center justify-center"
        style={{
          backgroundColor: colors.lemonChiffon,
          boxShadow: `0 0 0 2px ${colors.orangePeel}, 0 6px 12px rgba(0, 0, 0, 0.3)`,
          width: `${size + 32}px`,
          height: `${size + 32}px`,
        }}
      >
        {qrCodeUrl ? (
          <img 
            src={qrCodeUrl} 
            alt="QR Code" 
            width={size} 
            height={size}
            style={{
              display: 'block',
              maxWidth: '100%',
            }}
          />
        ) : (
          <div 
            className="flex items-center justify-center"
            style={{ width: size, height: size }}
          >
            <QrCode size={size * 0.8} style={{ color: colors.russet }} />
          </div>
        )}
      </div>
    </div>
  );
};

export default QRCodeDisplay;
