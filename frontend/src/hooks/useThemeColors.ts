import { useEffect, useState } from "react";
import { resolveThemeColor, type RGB } from "@/lib/themeColor";

/**
 * Resolves theme role tokens (e.g. "primary") to RGB for canvas drawing, and
 * re-resolves them whenever <html data-theme> changes. Pass a stable array —
 * a module-level constant — since a new array re-resolves on every render.
 */
export function useThemeColors(tokens: readonly string[]): RGB[] {
  const [colors, setColors] = useState<RGB[]>(() =>
    tokens.map(resolveThemeColor),
  );

  useEffect(() => {
    const resolve = () => setColors(tokens.map(resolveThemeColor));
    resolve();
    const observer = new MutationObserver(resolve);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });
    return () => observer.disconnect();
  }, [tokens]);

  return colors;
}
