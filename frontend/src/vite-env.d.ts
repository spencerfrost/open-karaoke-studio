/// <reference types="vite/client" />
/// <reference types="vite-plugin-pwa/client" />

interface ImportMetaEnv {
  /** Link for the entry page's "Watch the demo" button; hidden when unset. */
  readonly VITE_DEMO_RECORDING_URL?: string;
  /**
   * Base URL of the published docs site (the VitePress build of docs/), e.g.
   * https://example.com/docs/. The guided tour links each step's "how this
   * works" line to a page under it; the links are hidden when unset.
   */
  readonly VITE_DOCS_URL?: string;
}
