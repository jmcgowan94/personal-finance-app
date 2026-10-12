import { useMe, useUpdateMe } from "../../api/hooks";
import type { ThemePreference } from "../../api/types";
import { RANGE_PRESETS, type RangePreset } from "../../lib/filters";
import { applyTheme } from "../../lib/theme";

const THEME_OPTIONS: { value: string; label: string; pref: ThemePreference }[] = [
  { value: "system", label: "Use System Settings", pref: null },
  { value: "light", label: "Light Mode", pref: "light" },
  { value: "dark", label: "Dark Mode", pref: "dark" },
];

export function GeneralSettings() {
  const { data: me } = useMe();
  const update = useUpdateMe();

  function setTheme(value: string) {
    const theme = THEME_OPTIONS.find((o) => o.value === value)?.pref ?? null;
    const previous = me?.theme ?? null;
    applyTheme(theme); // switch immediately; the account save follows
    update.mutate({ theme }, { onError: () => applyTheme(previous) });
  }

  return (
    <section className="card">
      <h2>General Settings</h2>
      <div className="setting-row" style={{ marginTop: 16 }}>
        <label htmlFor="theme">Theme</label>
        <select id="theme" value={me?.theme ?? "system"} disabled={!me} onChange={(e) => setTheme(e.target.value)}>
          {THEME_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>
      <div className="setting-row" style={{ marginTop: 16 }}>
        <div>
          <label htmlFor="default-range">Default Time Window</label>
          <p className="muted setting-hint">The time window the Dashboard starts with when you open the app.</p>
        </div>
        <select
          id="default-range"
          value={me?.default_range ?? "all"}
          disabled={!me}
          onChange={(e) => update.mutate({ default_range: e.target.value as RangePreset })}
        >
          {RANGE_PRESETS.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
      </div>
      {update.isError && <p className="error">Could not save: {update.error.message}</p>}
    </section>
  );
}
