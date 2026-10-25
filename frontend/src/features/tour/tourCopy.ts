/**
 * tourCopy - what each step of the guided tour says, and what it points at.
 *
 * Written for a first-time visitor who is judging the developer: the main
 * line is plain words, and the technical detail lives in the "how this works"
 * line under it, with a link to the matching docs page.
 *
 * `targets` are `data-tour` ids. The first one found on screen anchors the
 * card; every one found gets a highlight ring. A step whose targets are all
 * off screen shows its card in the corner instead.
 */

import type { FallbackReason, TourStep } from "./tourSteps";

export interface StepCopy {
  title: string;
  body: string;
  /** One line for a technical reader. */
  how: string;
  /** Page on the docs site, relative to VITE_DOCS_URL. */
  docsPage?: string;
  /** `data-tour` ids: the first visible one anchors the card. */
  targets: string[];
  /** Ringed but never used as the anchor (too big to sit a card beside). */
  ringOnly?: string[];
  /** Which side of the anchor the card sits on. */
  side?: "top" | "right" | "bottom" | "left";
}

export const STEP_COPY: Partial<Record<TourStep, StepCopy>> = {
  sound: {
    title: "Turn your sound on",
    body: "This is karaoke, so you'll want to hear it. Turn your speakers up, then press the button.",
    how: "Browsers block sound until the page gets a click, so this button is also what lets the stage play audio later.",
    targets: [],
  },
  scan: {
    title: "Scan the code with your phone",
    body: "Your phone is the remote. Scan the code, search for any song you like and add it. No phone handy? Press “No phone? Open a phone view” under the code.",
    how: "Each phone joins this session over its own WebSocket, and everything the stage shows is kept per session.",
    docsPage: "architecture.html#session-management",
    targets: ["join-code"],
    side: "left",
  },
  wheel: {
    title: "Your song is getting ready",
    body: "It's being downloaded and the singer's voice is being taken out, and you can watch it happen in the corner. Meanwhile, spin the wheel: scroll, or use the arrow keys.",
    how: "A Celery worker downloads the audio, separates the vocals on the GPU with Demucs and Roformer models, then times the lyrics. Progress reaches every screen over a WebSocket.",
    docsPage: "architecture.html#processing-pipeline",
    targets: ["processing-list"],
    ringOnly: ["song-wheel"],
    side: "right",
  },
  ready: {
    title: "It's ready",
    body: "Press Sing this to start your song. Or pick anything else on the wheel.",
    how: "The job feed only says a job has left the queue, so the row asks the library whether the song came out playable before offering it.",
    docsPage: "websocket-protocol.html",
    targets: ["sing-this"],
    side: "right",
  },
  countdown: {
    title: "Get ready",
    body: "A quick count so the singer isn't caught off guard. The words show up as the song plays.",
    how: "The audio loads under the count. On 1 it waits until every track is decoded, so the song never starts early.",
    docsPage: "architecture.html#state-management",
    targets: [],
    ringOnly: ["countdown"],
  },
  controls: {
    title: "Now look at your phone",
    body: "When it's your turn, your phone opens the singer controls by itself. If it went to sleep, wake it and go back to the karaoke page.",
    how: "Each phone reports whether its page is on screen (Page Visibility API), so the stage knows when to ask the singer to open it.",
    docsPage: "architecture.html#websocket-architecture",
    targets: ["open-your-phone"],
    side: "bottom",
  },
  mix: {
    title: "Change the mix from your phone",
    body: "Move the Vocals slider on your phone and listen: the original singer's voice comes in or fades out, right here.",
    how: "The slider sends a performance-control message over the session socket, and the stage moves a Web Audio gain on the vocal track.",
    docsPage: "websocket-protocol.html",
    targets: ["vocal-level"],
    side: "right",
  },
};

/** The mix step's line when the singer has no phone linked. */
export const MIX_WITHOUT_PHONE_BODY =
  "Move your mouse to bring up the controls, then try the Vocals slider on the left. The original singer's voice comes in or fades out. A phone gets the same controls.";

export interface FallbackCopy {
  title: string;
  body: string;
  how: string;
  docsPage?: string;
}

export const FALLBACK_COPY: Record<FallbackReason, FallbackCopy> = {
  quota: {
    title: "The demo can't add new songs right now",
    body: "Its downloads are used up for now, but everything already in the songbook works. Try this one:",
    how: "Each demo session can add 3 new songs, and all demo visitors together 20 a day, so the GPU stays free for everyone.",
    docsPage: "demo-accounts.html",
  },
  busy: {
    title: "It's busy right now",
    body: "Other songs are ahead of yours, so it'll take a few minutes. Yours keeps going. Sing this one while you wait:",
    how: "Vocal separation runs one song at a time on a shared GPU, so songs wait their turn in the Celery queue.",
    docsPage: "architecture.html#processing-pipeline",
  },
  failed: {
    title: "Your song didn't make it",
    body: "Something went wrong getting it ready. That happens with some videos. Here's one that's ready to go:",
    how: "The worker retries out-of-memory and network failures by itself. This one still failed, so it shows as failed rather than retrying forever.",
    docsPage: "architecture.html#processing-pipeline",
  },
};

export const END_COPY = {
  title: "That's the whole loop",
  body: "You picked a song, watched it get made, sang it and ran the mix from a phone. Built by one developer, from the backend to this screen.",
  stack: [
    "FastAPI",
    "React 19 + TypeScript",
    "Celery + Redis",
    "Demucs and Roformer vocal separation",
    "WebSockets",
    "PostgreSQL",
  ],
  repoUrl: "https://github.com/spencerfrost/open-karaoke-studio",
};
