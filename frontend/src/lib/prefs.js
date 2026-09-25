import { useCallback, useState } from "react";

/**
 * A remembered on/off preference. Storage can be unavailable or throw (private
 * windows, blocked site data), so every access is guarded and the page works
 * the same without it — the choice just isn't remembered.
 */
export function usePref(key, fallback = false) {
  const [value, setValue] = useState(() => {
    try {
      const v = window.localStorage.getItem(key);
      return v === null ? fallback : v === "1";
    } catch {
      return fallback;
    }
  });

  const set = useCallback(
    (next) => {
      setValue(next);
      try {
        window.localStorage.setItem(key, next ? "1" : "0");
      } catch {
        /* not remembered — fine */
      }
    },
    [key]
  );

  return [value, set];
}
