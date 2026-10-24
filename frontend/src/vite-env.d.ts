/// <reference types="vite/client" />
/// <reference types="vite-plugin-pwa/client" />

interface ImportMetaEnv {
  /** Link for the entry page's "Watch the demo" button; hidden when unset. */
  readonly VITE_DEMO_RECORDING_URL?: string;
}
