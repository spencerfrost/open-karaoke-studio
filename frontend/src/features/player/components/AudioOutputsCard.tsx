/**
 * AudioOutputsCard - where this device plays the song, and where it sends
 * the lead vocal for the singer's headphones.
 *
 * Saved per device, like the theme: it describes the hardware plugged into
 * this computer, not the session.
 */

import React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { getAudioOutputs, useSettingsStore } from "@/stores/useSettingsStore";
import { canChooseAudioOutput } from "@/stores/shared/vocalMonitor";
import {
  useAudioOutputDevices,
  type AudioOutputDevice,
} from "../hooks/useAudioOutputDevices";

// Radix Select can't hold an empty value.
const NONE = "none";
const MAX_DELAY_MS = 300;

interface OutputSelectProps {
  id: string;
  label: string;
  hint: string;
  noneLabel: string;
  deviceId: string | null;
  savedLabel: string;
  devices: AudioOutputDevice[];
  onChange: (device: AudioOutputDevice | null) => void;
}

const OutputSelect: React.FC<OutputSelectProps> = ({
  id,
  label,
  hint,
  noneLabel,
  deviceId,
  savedLabel,
  devices,
  onChange,
}) => {
  const missing =
    deviceId !== null && !devices.some((d) => d.deviceId === deviceId);

  return (
    <div>
      <Label htmlFor={id} className="mb-1">
        {label}
      </Label>
      <p className="mb-2 text-sm text-muted-foreground">{hint}</p>
      <Select
        value={deviceId ?? NONE}
        onValueChange={(value) =>
          onChange(devices.find((d) => d.deviceId === value) ?? null)
        }
      >
        <SelectTrigger id={id} className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={NONE}>{noneLabel}</SelectItem>
          {devices.map((device) => (
            <SelectItem key={device.deviceId} value={device.deviceId}>
              {device.label}
            </SelectItem>
          ))}
          {missing && (
            <SelectItem value={deviceId}>
              {savedLabel || "Saved output"} (not connected)
            </SelectItem>
          )}
        </SelectContent>
      </Select>
      {missing && (
        <p className="mt-1 text-sm text-destructive">
          Not connected. Plug it back in or choose another output.
        </p>
      )}
    </div>
  );
};

/**
 * Applied on release, not while dragging: each change restarts the vocal in
 * the headphones to line it up again.
 */
const DelaySlider: React.FC<{
  delayMs: number;
  onCommit: (delayMs: number) => void;
}> = ({ delayMs, onCommit }) => {
  const [dragging, setDragging] = React.useState<number | null>(null);
  const shown = dragging ?? delayMs;

  return (
    <div>
      <p className="mb-1 text-sm font-medium">Headphones delay: {shown} ms</p>
      <p className="mb-3 text-sm text-muted-foreground">
        If the headphones sound ahead of the speakers, add delay until they line
        up. TVs often need some.
      </p>
      <Slider
        value={[shown]}
        min={0}
        max={MAX_DELAY_MS}
        step={5}
        onValueChange={([next]) => setDragging(next)}
        onValueCommit={([next]) => {
          setDragging(null);
          onCommit(next);
        }}
      />
    </div>
  );
};

const AudioOutputsCard: React.FC = () => {
  const audio = useSettingsStore((state) => state.audio);
  const setAudioSettings = useSettingsStore((state) => state.setAudioSettings);
  const outputs = getAudioOutputs(audio);
  const { devices, needsAccess, requestAccess } = useAudioOutputDevices();
  const supported = canChooseAudioOutput();

  return (
    <Card className="mb-4">
      <CardHeader>
        <CardTitle className="text-xl">Audio Outputs</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <p className="text-sm text-muted-foreground">
          For the screen that plays the songs. Saved on this device only.
        </p>

        {!supported ? (
          <p className="text-sm">
            This browser can't choose audio outputs. Use Chrome, Brave or Edge,
            opened at localhost or over https.
          </p>
        ) : (
          <>
            {needsAccess && (
              <div className="flex flex-col items-start gap-2">
                <p className="text-sm text-muted-foreground">
                  The browser lists audio outputs only after you allow the
                  microphone. Nothing is recorded.
                </p>
                <Button
                  variant="secondary"
                  onClick={() => void requestAccess()}
                >
                  Show outputs
                </Button>
              </div>
            )}

            <OutputSelect
              id="speakers-output"
              label="Speakers"
              hint="The song plays here, for the room."
              noneLabel="System default"
              deviceId={outputs.speakersDeviceId}
              savedLabel={outputs.speakersDeviceLabel}
              devices={devices}
              onChange={(device) =>
                setAudioSettings({
                  speakersDeviceId: device?.deviceId ?? null,
                  speakersDeviceLabel: device?.label ?? "",
                })
              }
            />

            <OutputSelect
              id="headphones-output"
              label="Singer's headphones"
              hint="The lead vocal plays here on its own, so the singer can hear the tune while the room hears the backing track. The singer sets its volume from their phone."
              noneLabel="Off"
              deviceId={outputs.headphonesDeviceId}
              savedLabel={outputs.headphonesDeviceLabel}
              devices={devices}
              onChange={(device) =>
                setAudioSettings({
                  headphonesDeviceId: device?.deviceId ?? null,
                  headphonesDeviceLabel: device?.label ?? "",
                })
              }
            />

            {outputs.headphonesDeviceId !== null && (
              <DelaySlider
                delayMs={outputs.headphonesDelayMs}
                onCommit={(next) =>
                  setAudioSettings({ headphonesDelayMs: next })
                }
              />
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
};

export default AudioOutputsCard;
