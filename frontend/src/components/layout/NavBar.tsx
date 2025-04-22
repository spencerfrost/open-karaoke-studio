import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Music, Upload, List, Settings } from 'lucide-react';
import vintageTheme from '../../utils/theme';

const NavBar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const colors = vintageTheme.colors;
  
  // Navigation items
  const navItems = [
    { name: 'Library', path: '/', icon: Music },
    { name: 'Add', path: '/add', icon: Upload },
    { name: 'Queue', path: '/queue', icon: List },
    { name: 'Settings', path: '/settings', icon: Settings },
  ];
  
  // Determine if a nav item is active
  const isActive = (path: string) => {
    return location.pathname === path;
  };
  
  return (
    <nav
      style={{
        backgroundColor: `${colors.russet}E6`,
        borderTop: `1px solid ${colors.orangePeel}`,
        position: 'sticky',
        bottom: 0,
        zIndex: 20,
      }}
      className="flex justify-around py-2"
    >
      {navItems.map((item) => {
        const active = isActive(item.path);
        const Icon = item.icon;
        
        return (
          <button
            key={item.name}
            onClick={() => navigate(item.path)}
            className="flex flex-col items-center px-4 py-2"
            style={{
              color: active ? colors.orangePeel : colors.lemonChiffon,
              opacity: active ? 1 : 0.7,
              transition: 'all 0.2s ease',
            }}
          >
            <Icon size={20} />
            <span className="text-xs mt-1">{item.name}</span>
          </button>
        );
      })}
    </nav>
  );
};

export default NavBar;
