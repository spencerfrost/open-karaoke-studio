import React, { ReactNode } from 'react';
import NavBar from './NavBar';
import { Music, Upload, List, Settings } from 'lucide-react';
import { useSettings } from '../../context/SettingsContext';
import vintageTheme from '../../utils/theme';

interface AppLayoutProps {
  children: ReactNode;
}

const navigationItems = [
  { name: 'Library', path: '/', icon: Music },
  { name: 'Add', path: '/add', icon: Upload },
  { name: 'Queue', path: '/queue', icon: List },
  { name: 'Settings', path: '/settings', icon: Settings },
];

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const { settings } = useSettings();
  
  // Background with vintage gradient
  const appBackground = {
    background: vintageTheme.background,
    color: vintageTheme.text.primary,
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column' as const,
  };
  
  return (
    <div style={appBackground}>
      {/* Texture overlay for vintage feel */}
      <div style={vintageTheme.getTextureOverlay()} />
      
      {/* Sunburst pattern - only shown in certain views if desired */}
      {settings.theme.themeName === 'vintage' && (
        <div style={vintageTheme.getSunburstPattern()} />
      )}
      
      {/* Main content */}
      <main className="flex-1 overflow-auto p-4 relative z-10">
        {children}
      </main>
      
      {/* Bottom navigation */}
      <NavBar
        items={navigationItems}
      />
    </div>
  );
};

export default AppLayout;
