/**
 * OpenYourPhonePrompt - asks the singer to take their phone out.
 *
 * Shown over the performance screen while a song plays and the singer's phone
 * is closed, locked or in the background. Nothing to tap: once the phone is
 * back on the page it sees its song has started and opens the controls itself,
 * and this goes away. A singer with no phone linked (a walk-up the host typed
 * in) never sees it.
 */

import React from "react";
import { Smartphone } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { needsPhoneOpened, usePresenceStore } from "@/stores/presenceStore";
import type { KaraokeQueueItemWithSong } from "@/types/KaraokeQueue";

interface OpenYourPhonePromptProps {
  current?: KaraokeQueueItemWithSong | null;
}

const OpenYourPhonePrompt: React.FC<OpenYourPhonePromptProps> = ({
  current,
}) => {
  const performerId = current?.performerId ?? null;
  const presence = usePresenceStore((s) =>
    performerId === null ? undefined : s.performers[performerId],
  );

  if (!current || !needsPhoneOpened(presence)) return null;

  return (
    <div className="pointer-events-none absolute inset-x-0 top-6 z-30 flex justify-center px-6">
      <Alert
        data-tour="open-your-phone"
        className="pointer-events-auto w-auto max-w-xl border-primary/60 px-6 py-4 shadow-lg [&>svg]:size-6"
      >
        <Smartphone className="text-primary" />
        <AlertTitle className="text-xl">
          {current.singer}, open your phone
        </AlertTitle>
        <AlertDescription className="text-base">
          Go back to the karaoke page on your phone to turn your voice up or
          down while you sing.
        </AlertDescription>
      </Alert>
    </div>
  );
};

export default OpenYourPhonePrompt;
