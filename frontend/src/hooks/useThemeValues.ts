import { useEffect, useState } from "react";
import { resolveThemeColor, type RGB } from "@/lib/themeColor";

/**
 * Resolves theme tokens and re-resolves them whenever <html data-theme>
 * changes. Pass a stable array — a module-level constant — since a new array
 * re-resolves on every render.
 */
function useThemeValues<T>(
  tokens: readonly string[],
  resolve: (token: string) => T,
): T[] {
  const [values, setValues] = useState<T[]>(() => tokens.map(resolve));

  useEffect(() => {
    const update = () => setValues(tokens.map(resolve));
    update();
    const observer = new MutationObserver(update);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });
    return () => observer.disconnect();
  }, [tokens, resolve]);

  return values;
}

const resolveThemeNumber = (token: string): number =>
  parseFloat(
    getComputedStyle(document.documentElement).getPropertyValue(`--${token}`),
  );

/** Theme role tokens (e.g. "primary") as RGB, for canvas drawing. */
export function useThemeColors(tokens: readonly string[]): RGB[] {
  return useThemeValues(tokens, resolveThemeColor);
}

/** Unitless numeric theme tokens (e.g. "visualizer-opacity"). */
export function useThemeNumbers(tokens: readonly string[]): number[] {
  return useThemeValues(tokens, resolveThemeNumber);
}
