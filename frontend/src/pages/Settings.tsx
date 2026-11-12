import React from "react";
import { useSettingsStore } from "../stores/useSettingsStore";
import AppLayout from "../components/layout/AppLayout";
import { RotationModeCard } from "@/features/session";
import { THEMES, isThemeName } from "@/lib/themes";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface SliderSettingProps {
  label: string;
  value: number;
  max: number;
  step?: number;
  onChange: (value: number) => void;
}

const SliderSetting: React.FC<SliderSettingProps> = ({
  label,
  value,
  max,
  step = 1,
  onChange,
}) => (
  <div>
    <p className="mb-3 text-sm font-medium">{label}</p>
    <Slider
      value={[value]}
      min={0}
      max={max}
      step={step}
      onValueChange={([next]) => onChange(next)}
    />
  </div>
);

interface SelectSettingProps {
  id: string;
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
}

const SelectSetting: React.FC<SelectSettingProps> = ({
  id,
  label,
  value,
  options,
  onChange,
}) => (
  <div>
    <Label htmlFor={id} className="mb-1">
      {label}
    </Label>
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger id={id} className="w-full">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {options.map((option) => (
          <SelectItem key={option.value} value={option.value}>
            {option.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  </div>
);

interface SwitchSettingProps {
  id: string;
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}

const SwitchSetting: React.FC<SwitchSettingProps> = ({
  id,
  label,
  checked,
  onChange,
}) => (
  <div className="flex items-center justify-between gap-4">
    <Label htmlFor={id}>{label}</Label>
    <Switch id={id} checked={checked} onCheckedChange={onChange} />
  </div>
);

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
        <h1 className="text-2xl font-semibold mb-6 text-primary">Settings</h1>

        <RotationModeCard />

        {/* Theme Settings */}
        <Card className="mb-4">
          <CardHeader>
            <CardTitle className="text-xl">Theme</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div>
              <Label htmlFor="theme-name" className="mb-1">
                Theme
              </Label>
              <p className="text-sm text-muted-foreground mb-2">
                Applies to this screen only.
              </p>
              <Select
                value={settings.theme.themeName}
                onValueChange={(value) => {
                  if (isThemeName(value)) {
                    setThemeSettings({ themeName: value });
                  }
                }}
              >
                <SelectTrigger id="theme-name" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {THEMES.map((theme) => (
                    <SelectItem key={theme.id} value={theme.id}>
                      {theme.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Audio Settings */}
        <Card className="mb-4">
          <CardHeader>
            <CardTitle className="text-xl">Audio</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-5">
            <SliderSetting
              label={`Default Vocals Volume: ${settings.audio.defaultVocalVolume}%`}
              value={settings.audio.defaultVocalVolume}
              max={100}
              onChange={(value) =>
                handleAudioChange("defaultVocalVolume", value)
              }
            />
            <SliderSetting
              label={`Default Instrumental Volume: ${settings.audio.defaultInstrumentalVolume}%`}
              value={settings.audio.defaultInstrumentalVolume}
              max={100}
              onChange={(value) =>
                handleAudioChange("defaultInstrumentalVolume", value)
              }
            />
            <SliderSetting
              label={`Fade-in Duration: ${settings.audio.fadeInDuration}ms`}
              value={settings.audio.fadeInDuration}
              max={2000}
              step={100}
              onChange={(value) => handleAudioChange("fadeInDuration", value)}
            />
            <SliderSetting
              label={`Fade-out Duration: ${settings.audio.fadeOutDuration}ms`}
              value={settings.audio.fadeOutDuration}
              max={2000}
              step={100}
              onChange={(value) => handleAudioChange("fadeOutDuration", value)}
            />
          </CardContent>
        </Card>

        {/* Processing Settings */}
        <Card className="mb-4">
          <CardHeader>
            <CardTitle className="text-xl">Processing</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <SelectSetting
              id="processing-quality"
              label="Quality"
              value={settings.processing.quality}
              options={[
                { value: "low", label: "Low" },
                { value: "medium", label: "Medium" },
                { value: "high", label: "High" },
              ]}
              onChange={(value) => handleProcessingChange("quality", value)}
            />
            <SelectSetting
              id="processing-output-format"
              label="Output Format"
              value={settings.processing.outputFormat}
              options={[
                { value: "mp3", label: "MP3" },
                { value: "wav", label: "WAV" },
              ]}
              onChange={(value) =>
                handleProcessingChange("outputFormat", value)
              }
            />
            <SwitchSetting
              id="auto-process-youtube"
              label="Auto-process YouTube"
              checked={settings.processing.autoProcessYouTube}
              onChange={(checked) =>
                handleProcessingChange("autoProcessYouTube", checked)
              }
            />
          </CardContent>
        </Card>

        {/* Display Settings */}
        <Card className="mb-4">
          <CardHeader>
            <CardTitle className="text-xl">Display</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <SelectSetting
              id="lyrics-size"
              label="Lyrics Size"
              value={settings.display.lyricsSize}
              options={[
                { value: "small", label: "Small" },
                { value: "medium", label: "Medium" },
                { value: "large", label: "Large" },
              ]}
              onChange={(value) => handleDisplayChange("lyricsSize", value)}
            />
            <SwitchSetting
              id="show-audio-visualizations"
              label="Show Audio Visualizations"
              checked={settings.display.showAudioVisualizations}
              onChange={(checked) =>
                handleDisplayChange("showAudioVisualizations", checked)
              }
            />
            <SwitchSetting
              id="show-progress"
              label="Show Progress Bar"
              checked={settings.display.showProgress}
              onChange={(checked) =>
                handleDisplayChange("showProgress", checked)
              }
            />
            <SwitchSetting
              id="song-previews-enabled"
              label="Preview Songs on Hover in the Songbook"
              checked={settings.display.songPreviewsEnabled ?? true}
              onChange={(checked) =>
                handleDisplayChange("songPreviewsEnabled", checked)
              }
            />
          </CardContent>
        </Card>

        {/* Reset Button */}
        <Button
          variant="secondary"
          onClick={handleResetSettings}
          className="mt-4"
        >
          Reset All Settings
        </Button>
      </div>
    </AppLayout>
  );
};

export default SettingsPage;
