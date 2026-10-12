import { useMe, useUpdateMe } from "../../api/hooks";
import { applyTheme, currentTheme, resolveTheme } from "../../lib/theme";

export function GeneralSettings() {
  const { data: me } = useMe();
  const update = useUpdateMe();
  const dark = (me ? resolveTheme(me.theme) : currentTheme()) === "dark";

  function setDark(next: boolean) {
    const previous = me?.theme ?? null;
    const theme = next ? "dark" : "light";
    applyTheme(theme); // switch immediately; the account save follows
    update.mutate({ theme }, { onError: () => applyTheme(previous) });
  }

  return (
    <section className="card">
      <h2>General Settings</h2>
      <div className="switch-row" style={{ marginTop: 16 }}>
        <div>
          <div id="dark-mode-label">Dark mode</div>
          <p className="muted">
            {me?.theme === null ? "Currently following your device's setting." : "Applies to the whole app."}
          </p>
        </div>
        <button
          type="button"
          role="switch"
          className="switch"
          aria-checked={dark}
          aria-labelledby="dark-mode-label"
          disabled={!me}
          onClick={() => setDark(!dark)}
        />
      </div>
      {update.isError && <p className="error">Could not save: {update.error.message}</p>}
    </section>
  );
}
