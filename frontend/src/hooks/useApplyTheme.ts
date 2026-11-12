import { useEffect } from "react";
import { DEFAULT_THEME, isThemeName } from "@/lib/themes";
import { resolveThemeColor } from "@/lib/themeColor";
import { useSettingsStore } from "@/stores/useSettingsStore";

const toHex = (rgb: number[]) =>
  `#${rgb.map((c) => c.toString(16).padStart(2, "0")).join("")}`;

/**
 * Puts the chosen theme on <html data-theme> and matches the browser chrome
 * (theme-color) to its primary. index.html sets data-theme before React
 * loads, so this only takes over once the app is running.
 */
export function useApplyTheme() {
  const themeName = useSettingsStore((state) => state.theme.themeName);

  useEffect(() => {
    const theme = isThemeName(themeName) ? themeName : DEFAULT_THEME;
    document.documentElement.dataset.theme = theme;
    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute("content", toHex(resolveThemeColor("primary")));
  }, [themeName]);
}
