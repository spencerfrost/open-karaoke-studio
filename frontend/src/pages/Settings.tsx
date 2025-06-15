import React from "react";
import { useSettingsStore } from "../stores/useSettingsStore";
import AppLayout from "../components/layout/AppLayout";

const SettingsPage: React.FC = () => {
  // Use the Zustand store instead of the Context API
  const settings = useSettingsStore((state) => state);
  const setThemeSettings = useSettingsStore((state) => state.setThemeSettings);
  const setAudioSettings = useSettingsStore((state) => state.setAudioSettings);
  const setProcessingSettings = useSettingsStore(
    (state) => state.setProcessingSettings,
  );
  const setDisplaySettings = useSettingsStore(
    (state) => state.setDisplaySettings,
  );
  const resetSettings = useSettingsStore((state) => state.resetSettings);

  // Handler for theme settings
  const handleThemeChange = (setting: string, value: string | boolean) => {
    setThemeSettings({ [setting]: value });
  };

  // Handler for audio settings
  const handleAudioChange = (setting: string, value: number) => {
    setAudioSettings({ [setting]: value });
  };

  // Handler for processing settings
  const handleProcessingChange = (setting: string, value: string | boolean) => {
    setProcessingSettings({ [setting]: value });
  };

  // Handler for display settings
  const handleDisplayChange = (setting: string, value: string | boolean) => {
    setDisplaySettings({ [setting]: value });
  };

  // Handler for reset settings
  const handleResetSettings = () => {
    resetSettings();
  };

  return (
    <AppLayout>
      <div>
        <h1 className="text-2xl font-semibold mb-6 text-orange-peel">
          Settings
        </h1>

        {/* Theme Settings */}
        <div className="bg-lemon-chiffon text-russet shadow-lg border border-orange-peel overflow-hidden mb-4 p-4 rounded-lg">
          <h2 className="text-xl mb-3">Theme</h2>
          <div className="flex flex-col gap-4">
            <div>
              <label className="block mb-1">Dark Mode</label>
              <input
                type="checkbox"
                checked={settings.theme.darkMode}
                onChange={(e) =>
                  handleThemeChange("darkMode", e.target.checked)
                }
                className="p-2 border border-orange-peel bg-lemon-chiffon/80 text-russet rounded"
              />
            </div>
            <div>
              <label className="block mb-1">Theme Style</label>
              <select
                value={settings.theme.themeName}
                onChange={(e) => handleThemeChange("themeName", e.target.value)}
                className="p-2 border border-orange-peel bg-lemon-chiffon/80 text-russet rounded w-full"
              >
                <option value="vintage">Vintage</option>
                <option value="synthwave">Synthwave</option>
                <option value="minimal">Minimal</option>
              </select>
            </div>
          </div>
        </div>

        {/* Audio Settings */}
        <div className="bg-lemon-chiffon text-russet shadow-lg border border-orange-peel overflow-hidden mb-4 p-4 rounded-lg">
          <h2 className="text-xl mb-3">Audio</h2>
          <div className="flex flex-col gap-4">
            <div>
              <label className="block mb-1">
                Default Vocals Volume: {settings.audio.defaultVocalVolume}%
              </label>
              <input
                type="range"
                min="0"
                max="100"
                value={settings.audio.defaultVocalVolume}
                onChange={(e) =>
                  handleAudioChange(
                    "defaultVocalVolume",
                    Number(e.target.value),
                  )
                }
                className="w-full"
              />
            </div>
            <div>
              <label className="block mb-1">
                Default Instrumental Volume:{" "}
                {settings.audio.defaultInstrumentalVolume}%
              </label>
              <input
                type="range"
                min="0"
                max="100"
                value={settings.audio.defaultInstrumentalVolume}
                onChange={(e) =>
                  handleAudioChange(
                    "defaultInstrumentalVolume",
                    Number(e.target.value),
                  )
                }
                className="w-full"
              />
            </div>
            <div>
              <label className="block mb-1">
                Fade-in Duration: {settings.audio.fadeInDuration}ms
              </label>
              <input
                type="range"
                min="0"
                max="2000"
                step="100"
                value={settings.audio.fadeInDuration}
                onChange={(e) =>
                  handleAudioChange("fadeInDuration", Number(e.target.value))
                }
                className="w-full"
              />
            </div>
            <div>
              <label className="block mb-1">
                Fade-out Duration: {settings.audio.fadeOutDuration}ms
              </label>
              <input
                type="range"
                min="0"
                max="2000"
                step="100"
                value={settings.audio.fadeOutDuration}
                onChange={(e) =>
                  handleAudioChange("fadeOutDuration", Number(e.target.value))
                }
                className="w-full"
              />
            </div>
          </div>
        </div>

        {/* Processing Settings */}
        <div className="bg-lemon-chiffon text-russet shadow-lg border border-orange-peel overflow-hidden mb-4 p-4 rounded-lg">
          <h2 className="text-xl mb-3">Processing</h2>
          <div className="flex flex-col gap-4">
            <div>
              <label className="block mb-1">Quality</label>
              <select
                value={settings.processing.quality}
                onChange={(e) =>
                  handleProcessingChange("quality", e.target.value)
                }
                className="p-2 border border-orange-peel bg-lemon-chiffon/80 text-russet rounded w-full"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>
            <div>
              <label className="block mb-1">Output Format</label>
              <select
                value={settings.processing.outputFormat}
                onChange={(e) =>
                  handleProcessingChange("outputFormat", e.target.value)
                }
                className="p-2 border border-orange-peel bg-lemon-chiffon/80 text-russet rounded w-full"
              >
                <option value="mp3">MP3</option>
                <option value="wav">WAV</option>
              </select>
            </div>
            <div>
              <label className="block mb-1">Auto-process YouTube</label>
              <input
                type="checkbox"
                checked={settings.processing.autoProcessYouTube}
                onChange={(e) =>
                  handleProcessingChange("autoProcessYouTube", e.target.checked)
                }
                className="p-2 border border-orange-peel bg-lemon-chiffon/80 text-russet rounded"
              />
            </div>
          </div>
        </div>

        {/* Display Settings */}
        <div className="bg-lemon-chiffon text-russet shadow-lg border border-orange-peel overflow-hidden mb-4 p-4 rounded-lg">
          <h2 className="text-xl mb-3">Display</h2>
          <div className="flex flex-col gap-4">
            <div>
              <label className="block mb-1">Lyrics Size</label>
              <select
                value={settings.display.lyricsSize}
                onChange={(e) =>
                  handleDisplayChange("lyricsSize", e.target.value)
                }
                className="p-2 border border-orange-peel bg-lemon-chiffon/80 text-russet rounded w-full"
              >
                <option value="small">Small</option>
                <option value="medium">Medium</option>
                <option value="large">Large</option>
              </select>
            </div>
            <div>
              <label className="block mb-1">Show Audio Visualizations</label>
              <input
                type="checkbox"
                checked={settings.display.showAudioVisualizations}
                onChange={(e) =>
                  handleDisplayChange(
                    "showAudioVisualizations",
                    e.target.checked,
                  )
                }
                className="p-2 border border-orange-peel bg-lemon-chiffon/80 text-russet rounded"
              />
            </div>
            <div>
              <label className="block mb-1">Show Progress Bar</label>
              <input
                type="checkbox"
                checked={settings.display.showProgress}
                onChange={(e) =>
                  handleDisplayChange("showProgress", e.target.checked)
                }
                className="p-2 border border-orange-peel bg-lemon-chiffon/80 text-russet rounded"
              />
            </div>
          </div>
        </div>

        {/* Reset Button */}
        <button
          onClick={handleResetSettings}
          className="bg-rust text-lemon-chiffon px-4 py-2 rounded mt-4"
        >
          Reset All Settings
        </button>
      </div>
    </AppLayout>
  );
};

export default SettingsPage;
