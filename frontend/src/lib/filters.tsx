import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

export type RangePreset = "3m" | "6m" | "12m" | "ytd" | "all";

export const RANGE_PRESETS: { value: RangePreset; label: string }[] = [
  { value: "3m", label: "Last 3 months" },
  { value: "6m", label: "Last 6 months" },
  { value: "12m", label: "Last 12 months" },
  { value: "ytd", label: "Year to date" },
  { value: "all", label: "All time" },
];

export interface DashboardFilters {
  range: RangePreset;
  accountId: number | null;
}

function isoDate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Turn a preset into the API's date_from (whole calendar months, including this one). */
export function rangeStart(range: RangePreset, today = new Date()): string | undefined {
  switch (range) {
    case "all":
      return undefined;
    case "ytd":
      return isoDate(new Date(today.getFullYear(), 0, 1));
    default: {
      const months = Number.parseInt(range, 10);
      return isoDate(new Date(today.getFullYear(), today.getMonth() - (months - 1), 1));
    }
  }
}

export function filterParams(f: DashboardFilters) {
  return { date_from: rangeStart(f.range), account_id: f.accountId ?? undefined };
}

const FiltersContext = createContext<{
  filters: DashboardFilters;
  setFilters: (f: DashboardFilters) => void;
  /** False until the user's default time window is known; queries wait for it. */
  ready: boolean;
} | null>(null);

/**
 * The time window and account start at the user's saved defaults (General Settings).
 * Picking others on a page applies for the rest of the visit without changing them.
 */
export function FiltersProvider({
  defaultRange,
  defaultAccountId,
  ready,
  children,
}: {
  defaultRange: RangePreset;
  defaultAccountId: number | null;
  ready: boolean;
  children: ReactNode;
}) {
  // null = not chosen this visit, so the saved default applies.
  const [chosenRange, setChosenRange] = useState<RangePreset | null>(null);
  // Wrapped because null ("All accounts") is itself a valid choice.
  const [chosenAccount, setChosenAccount] = useState<{ id: number | null } | null>(null);
  const value = useMemo(
    () => ({
      filters: { range: chosenRange ?? defaultRange, accountId: chosenAccount ? chosenAccount.id : defaultAccountId },
      setFilters: (f: DashboardFilters) => {
        setChosenRange(f.range);
        setChosenAccount({ id: f.accountId });
      },
      ready,
    }),
    [chosenRange, defaultRange, chosenAccount, defaultAccountId, ready],
  );
  return <FiltersContext.Provider value={value}>{children}</FiltersContext.Provider>;
}

export function useFilters() {
  const ctx = useContext(FiltersContext);
  if (!ctx) throw new Error("useFilters must be used inside FiltersProvider");
  return ctx;
}
