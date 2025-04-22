import React from 'react';
import { useSettings } from '../context/SettingsContext';
import AppLayout from '../components/layout/AppLayout';
import vintageTheme from '../utils/theme';

const SettingsPage: React.FC = () => {
  const { settings, dispatch } = useSettings();
  const colors = vintageTheme.colors;
  
  // Handler for theme settings
  const handleThemeChange = (setting: string, value: any) => {
    dispatch({
      type: 'SET_THEME_SETTINGS',
      payload: { [setting]: value }
    });
  };
  
  // Handler for audio settings
  const handleAudioChange = (setting: string, value: any) => {
    dispatch({
      type: 'SET_AUDIO_SETTINGS',
      payload: { [setting]: value }
    });
  };
  
  // Handler for processing settings
  const handleProcessingChange = (setting: string, value: any) => {
    dispatch({
      type: 'SET_PROCESSING_SETTINGS',
      payload: { [setting]: value }
    });
  };
  
  // Handler for display settings
  const handleDisplayChange = (setting: string, value: any) => {
    dispatch({
      type: 'SET_DISPLAY_SETTINGS',
      payload: { [setting]: value }
    });
  };
  
  // Handler for reset settings
  const handleResetSettings = () => {
    dispatch({ type: 'RESET_SETTINGS' });
  };
  
  // Shared card style
  const cardStyle = {
    backgroundColor: colors.lemonChiffon,
    color: colors.russet,
    boxShadow: `0 4px 6px rgba(0, 0, 0, 0.2), inset 0 0 0 1px ${colors.orangePeel}`,
    overflow: 'hidden',
    marginBottom: '1rem'
  };
  
  // Shared input styles
  const inputStyle = {
    backgroundColor: `${colors.lemonChiffon}80`,
    borderColor: colors.orangePeel,
    color: colors.russet
  };
  
  return (
    <AppLayout>
      <div>
        <h1 
          className="text-2xl font-semibold mb-6"
          style={{ color: colors.orangePeel }}
        >
          Settings
        </h1>
        
        {/* Theme Settings */}
        <div className="rounded-lg overflow-hidden" style={cardStyle}>
          <div className="p-4 border-b" style={{ borderColor: `${colors.orangePeel}30` }}>
            <h2 className="font-medium mb-3">Theme Settings</h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-sm opacity-75">Theme</label>
                <select 
                  className="border rounded p-1 text-sm focus:outline-none"
                  style={inputStyle}
                  value={settings.theme.themeName}
                  onChange={(e) => handleThemeChange('themeName', e.target.value)}
                >
                  <option value="vintage">Vintage Sign</option>
                  <option value="synthwave">Synthwave</option>
                  <option value="minimal">Minimal</option>
                </select>
              </div>
              <div className="flex items-center justify-between">
                <label className="text-sm opacity-75">Dark Mode</label>
                <div className="relative inline-block w-10 mr-2 align-middle select-none">
                  <input 
                    type="checkbox" 
                    id="toggle-dark-mode" 
                    className="sr-only"
                    checked={settings.theme.darkMode}
                    onChange={(e) => handleThemeChange('darkMode', e.target.checked)}
                  />
                  <div className="h-4 bg-gray-400 rounded-full w-10"></div>
                  <div 
                    className="absolute w-6 h-6 rounded-full -top-1 transition transform"
                    style={{
                      backgroundColor: colors.darkCyan,
                      transform: settings.theme.darkMode ? 'translateX(1rem)' : 'translateX(0)'
                    }}
                  ></div>
                </div>
              </div>
            </div>
          </div>
          
          {/* Audio Settings */}
          <div className="p-4 border-b" style={{ borderColor: `${colors.orangePeel}30` }}>
            <h2 className="font-medium mb-3">Audio Settings</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-sm opacity-75 mb-1">Default Vocal Volume</label>
                <div className="flex items-center gap-2">
                  <input 
                    type="range" 
                    className="w-full"
                    min="0" 
                    max="100"
                    value={settings.audio.defaultVocalVolume}
                    onChange={(e) => handleAudioChange('defaultVocalVolume', parseInt(e.target.value))}
                    style={{ accentColor: colors.darkCyan }}
                  />
                  <span className="text-sm opacity-75 w-8 text-right">
                    {settings.audio.defaultVocalVolume}%
                  </span>
                </div>
              </div>
              <div>
                <label className="block text-sm opacity-75 mb-1">Default Instrumental Volume</label>
                <div className="flex items-center gap-2">
                  <input 
                    type="range" 
                    className="w-full"
                    min="0" 
                    max="100"
                    value={settings.audio.defaultInstrumentalVolume}
                    onChange={(e) => handleAudioChange('defaultInstrumentalVolume', parseInt(e.target.value))}
                    style={{ accentColor: colors.darkCyan }}
                  />
                  <span className="text-sm opacity-75 w-8 text-right">
                    {settings.audio.defaultInstrumentalVolume}%
                  </span>
                </div>
              </div>
              <div>
                <label className="block text-sm opacity-75 mb-1">Fade Duration (ms)</label>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs opacity-75 mb-1">Fade In</label>
                    <input 
                      type="number" 
                      className="w-full border rounded px-2 py-1 focus:outline-none"
                      style={inputStyle}
                      value={settings.audio.fadeInDuration}
                      onChange={(e) => handleAudioChange('fadeInDuration', parseInt(e.target.value))}
                      min="0"
                      step="100"
                    />
                  </div>
                  <div>
                    <label className="block text-xs opacity-75 mb-1">Fade Out</label>
                    <input 
                      type="number" 
                      className="w-full border rounded px-2 py-1 focus:outline-none"
                      style={inputStyle}
                      value={settings.audio.fadeOutDuration}
                      onChange={(e) => handleAudioChange('fadeOutDuration', parseInt(e.target.value))}
                      min="0"
                      step="100"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          {/* Processing Settings */}
          <div className="p-4 border-b" style={{ borderColor: `${colors.orangePeel}30` }}>
            <h2 className="font-medium mb-3">Processing Settings</h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-sm opacity-75">Processing Quality</label>
                <select 
                  className="border rounded p-1 text-sm focus:outline-none"
                  style={inputStyle}
                  value={settings.processing.quality}
                  onChange={(e) => handleProcessingChange('quality', e.target.value)}
                >
                  <option value="low">Low (Faster)</option>
                  <option value="medium">Medium</option>
                  <option value="high">High (Slower)</option>
                </select>
              </div>
              <div className="flex items-center justify-between">
                <label className="text-sm opacity-75">Output Format</label>
                <select 
                  className="border rounded p-1 text-sm focus:outline-none"
                  style={inputStyle}
                  value={settings.processing.outputFormat}
                  onChange={(e) => handleProcessingChange('outputFormat', e.target.value)}
                >
                  <option value="mp3">MP3</option>
                  <option value="wav">WAV</option>
                </select>
              </div>
              <div className="flex items-center justify-between">
                <label className="text-sm opacity-75">Auto-Process YouTube Videos</label>
                <div className="relative inline-block w-10 mr-2 align-middle select-none">
                  <input 
                    type="checkbox" 
                    id="toggle-auto-process" 
                    className="sr-only"
                    checked={settings.processing.autoProcessYouTube}
                    onChange={(e) => handleProcessingChange('autoProcessYouTube', e.target.checked)}
                  />
                  <div className="h-4 bg-gray-400 rounded-full w-10"></div>
                  <div 
                    className="absolute w-6 h-6 rounded-full -top-1 transition transform"
                    style={{
                      backgroundColor: colors.darkCyan,
                      transform: settings.processing.autoProcessYouTube ? 'translateX(1rem)' : 'translateX(0)'
                    }}
                  ></div>
                </div>
              </div>
            </div>
          </div>
          
          {/* Display Settings */}
          <div className="p-4">
            <h2 className="font-medium mb-3">Display Settings</h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-sm opacity-75">Lyrics Size</label>
                <select 
                  className="border rounded p-1 text-sm focus:outline-none"
                  style={inputStyle}
                  value={settings.display.lyricsSize}
                  onChange={(e) => handleDisplayChange('lyricsSize', e.target.value)}
                >
                  <option value="small">Small</option>
                  <option value="medium">Medium</option>
                  <option value="large">Large</option>
                </select>
              </div>
              <div className="flex items-center justify-between">
                <label className="text-sm opacity-75">Show Audio Visualizations</label>
                <div className="relative inline-block w-10 mr-2 align-middle select-none">
                  <input 
                    type="checkbox" 
                    id="toggle-visualizations" 
                    className="sr-only"
                    checked={settings.display.showAudioVisualizations}
                    onChange={(e) => handleDisplayChange('showAudioVisualizations', e.target.checked)}
                  />
                  <div className="h-4 bg-gray-400 rounded-full w-10"></div>
                  <div 
                    className="absolute w-6 h-6 rounded-full -top-1 transition transform"
                    style={{
                      backgroundColor: colors.darkCyan,
                      transform: settings.display.showAudioVisualizations ? 'translateX(1rem)' : 'translateX(0)'
                    }}
                  ></div>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <label className="text-sm opacity-75">Show Progress Bar</label>
                <div className="relative inline-block w-10 mr-2 align-middle select-none">
                  <input 
                    type="checkbox" 
                    id="toggle-progress" 
                    className="sr-only"
                    checked={settings.display.showProgress}
                    onChange={(e) => handleDisplayChange('showProgress', e.target.checked)}
                  />
                  <div className="h-4 bg-gray-400 rounded-full w-10"></div>
                  <div 
                    className="absolute w-6 h-6 rounded-full -top-1 transition transform"
                    style={{
                      backgroundColor: colors.darkCyan,
                      transform: settings.display.showProgress ? 'translateX(1rem)' : 'translateX(0)'
                    }}
                  ></div>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        {/* Reset Button */}
        <button
          className="w-full py-2 rounded mt-4 transition-colors hover:opacity-90"
          style={{
            backgroundColor: colors.rust,
            color: colors.lemonChiffon,
            border: `1px solid ${colors.lemonChiffon}`
          }}
          onClick={handleResetSettings}
        >
          Reset to Default Settings
        </button>
      </div>
    </AppLayout>
  );
};

export default SettingsPage;
