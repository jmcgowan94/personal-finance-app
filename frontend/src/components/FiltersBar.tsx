import { useAccounts } from "../api/hooks";
import { RANGE_PRESETS, useFilters, type RangePreset } from "../lib/filters";

export function FiltersBar() {
  const { filters, setFilters } = useFilters();
  const { data: accounts = [] } = useAccounts();
  return (
    <div className="toolbar">
      <select
        aria-label="Date range"
        value={filters.range}
        onChange={(e) => setFilters({ ...filters, range: e.target.value as RangePreset })}
      >
        {RANGE_PRESETS.map((p) => (
          <option key={p.value} value={p.value}>
            {p.label}
          </option>
        ))}
      </select>
      <select
        aria-label="Account"
        value={filters.accountId ?? ""}
        onChange={(e) => setFilters({ ...filters, accountId: e.target.value ? Number(e.target.value) : null })}
      >
        <option value="">All accounts</option>
        {accounts.map((a) => (
          <option key={a.id} value={a.id}>
            {a.name}
          </option>
        ))}
      </select>
    </div>
  );
}
