import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "theme";
const THEME_COLOR = { light: "#F7F6F2", dark: "#141311" };

/** The saved choice, or else the operating system's preference. */
function initialTheme() {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved === "light" || saved === "dark") return saved;
  } catch {
    /* storage unavailable — fall through to the OS preference */
  }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function apply(theme) {
  document.documentElement.classList.toggle("dark", theme === "dark");
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", THEME_COLOR[theme]);
}

/**
 * Light / dark theme. The `dark` class on <html> drives every colour (see the
 * CSS variables in index.css). The inline script in index.html applies the
 * saved theme before first paint, so a reload never flashes the wrong one; this
 * hook keeps React state in step with it and saves changes.
 */
export function useTheme() {
  const [theme, setTheme] = useState(initialTheme);

  useEffect(() => {
    apply(theme);
  }, [theme]);

  const toggle = useCallback(() => {
    setTheme((current) => {
      const next = current === "dark" ? "light" : "dark";
      try {
        window.localStorage.setItem(STORAGE_KEY, next);
      } catch {
        /* not remembered — the toggle still works for this visit */
      }
      return next;
    });
  }, []);

  return { theme, isDark: theme === "dark", toggle };
}
