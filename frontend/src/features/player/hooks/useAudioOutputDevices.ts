import { useCallback, useEffect, useState } from "react";
import { createLogger } from "@/lib/logger";

const logger = createLogger("hook:useAudioOutputDevices");

export interface AudioOutputDevice {
  deviceId: string;
  label: string;
}

/**
 * The audio outputs this device can play to, kept current as things are
 * plugged in and out.
 *
 * Browsers list outputs only once the page may use the microphone, so until
 * then the list is empty and `needsAccess` is true. `requestAccess` asks,
 * releases the microphone at once, and lists again.
 */
export function useAudioOutputDevices() {
  const [devices, setDevices] = useState<AudioOutputDevice[]>([]);
  const [needsAccess, setNeedsAccess] = useState(false);

  const refresh = useCallback(async () => {
    if (!navigator.mediaDevices?.enumerateDevices) return;
    try {
      const all = await navigator.mediaDevices.enumerateDevices();
      // "default" and "communications" are aliases of real devices listed
      // alongside them; without access every id is blank.
      const outputs = all.filter(
        (device) =>
          device.kind === "audiooutput" &&
          device.deviceId !== "" &&
          device.deviceId !== "default" &&
          device.deviceId !== "communications",
      );
      setDevices(
        outputs.map((device, index) => ({
          deviceId: device.deviceId,
          label: device.label || `Output ${index + 1}`,
        })),
      );
      setNeedsAccess(outputs.length === 0);
    } catch (error) {
      logger.warn("Could not list audio outputs:", error);
    }
  }, []);

  const requestAccess = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });
      for (const track of stream.getTracks()) track.stop();
    } catch (error) {
      logger.warn("Microphone access refused:", error);
    }
    await refresh();
  }, [refresh]);

  useEffect(() => {
    void refresh();
    const mediaDevices = navigator.mediaDevices;
    if (!mediaDevices) return;
    const onChange = () => void refresh();
    mediaDevices.addEventListener("devicechange", onChange);
    return () => mediaDevices.removeEventListener("devicechange", onChange);
  }, [refresh]);

  return { devices, needsAccess, requestAccess };
}
