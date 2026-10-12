import { useMe, useUpdateMe } from "../../api/hooks";
import type { ThemePreference } from "../../api/types";
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
      {update.isError && <p className="error">Could not save: {update.error.message}</p>}
    </section>
  );
}
