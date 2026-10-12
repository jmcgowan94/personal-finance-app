import { useEffect } from "react";

import { useMe } from "../api/hooks";
import type { ThemePreference } from "../api/types";

// The choice is stored on the user's account; this local copy lets index.html
// apply it before the page first draws. Keep the key in sync with index.html.
const STORAGE_KEY = "theme";
const DEVICE_DARK = "(prefers-color-scheme: dark)";

export type Theme = "light" | "dark";

export function resolveTheme(pref: ThemePreference): Theme {
  return pref ?? (window.matchMedia(DEVICE_DARK).matches ? "dark" : "light");
}

export function applyTheme(pref: ThemePreference) {
  document.documentElement.dataset.theme = resolveTheme(pref);
  try {
    if (pref) localStorage.setItem(STORAGE_KEY, pref);
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Storage unavailable; the account setting still applies once loaded.
  }
}

/** Keep the page's theme in line with the user's saved preference (or the device). */
export function useSyncTheme() {
  const { data: me } = useMe();
  const pref = me?.theme;

  useEffect(() => {
    if (pref === undefined) return; // not loaded yet; index.html already applied the cached choice
    applyTheme(pref);
    if (pref !== null) return;
    const mq = window.matchMedia(DEVICE_DARK);
    const onChange = () => applyTheme(null);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [pref]);
}
