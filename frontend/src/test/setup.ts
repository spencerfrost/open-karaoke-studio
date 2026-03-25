import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeAll, afterAll, vi } from "vitest";
import { server } from "./mocks/server";

// Extend Vitest matchers with jest-dom
// This is handled by the import above

// --- Global Mocks ---

// Mock ResizeObserver (not available in jsdom)
class ResizeObserverMock {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
vi.stubGlobal("ResizeObserver", ResizeObserverMock);

// Mock matchMedia (not available in jsdom)
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock IntersectionObserver (not available in jsdom)
class IntersectionObserverMock {
  readonly root: Element | null = null;
  readonly rootMargin: string = "";
  readonly thresholds: ReadonlyArray<number> = [];
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
  takeRecords = vi.fn().mockReturnValue([]);
}
vi.stubGlobal("IntersectionObserver", IntersectionObserverMock);

// Mock scrollTo (not implemented in jsdom)
window.scrollTo = vi.fn();
Element.prototype.scrollTo = vi.fn();
Element.prototype.scrollIntoView = vi.fn();

// Mock Web Audio API
class AudioContextMock {
  state = "running";
  currentTime = 0;
  destination = {};
  sampleRate = 44100;

  createBufferSource = vi.fn().mockReturnValue({
    buffer: null,
    connect: vi.fn().mockReturnThis(),
    start: vi.fn(),
    stop: vi.fn(),
    onended: null,
  });

  createGain = vi.fn().mockReturnValue({
    gain: { value: 1 },
    connect: vi.fn().mockReturnThis(),
  });

  createAnalyser = vi.fn().mockReturnValue({
    fftSize: 256,
    frequencyBinCount: 128,
    connect: vi.fn().mockReturnThis(),
    getByteTimeDomainData: vi.fn(),
    getByteFrequencyData: vi.fn(),
  });

  decodeAudioData = vi.fn().mockResolvedValue({
    duration: 180,
    length: 7938000,
    numberOfChannels: 2,
    sampleRate: 44100,
  });

  close = vi.fn().mockResolvedValue(undefined);
  resume = vi.fn().mockResolvedValue(undefined);
  suspend = vi.fn().mockResolvedValue(undefined);
}
vi.stubGlobal("AudioContext", AudioContextMock);

// Mock URL.createObjectURL and revokeObjectURL
URL.createObjectURL = vi.fn(() => "blob:mock-url");
URL.revokeObjectURL = vi.fn();

// --- MSW Setup ---

beforeAll(() => {
  server.listen({ onUnhandledRequest: "warn" });
});

afterEach(() => {
  cleanup();
  server.resetHandlers();
});

afterAll(() => {
  server.close();
});
