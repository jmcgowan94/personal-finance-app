const currency = new Intl.NumberFormat(undefined, { style: "currency", currency: "USD" });
const wholeCurrency = new Intl.NumberFormat(undefined, {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});
const compactCurrency = new Intl.NumberFormat(undefined, {
  style: "currency",
  currency: "USD",
  notation: "compact",
  maximumFractionDigits: 1,
});

export const toNumber = (value: string | number) => (typeof value === "number" ? value : Number(value));

export const formatMoney = (value: string | number) => currency.format(toNumber(value));

/** Axis ticks and bar labels: $0, $972, $1.2K */
export const formatMoneyCompact = (value: string | number) => {
  const n = toNumber(value);
  return Math.abs(n) < 1000 ? wholeCurrency.format(n) : compactCurrency.format(n);
};

export function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export function formatMonth(month: string, style: "short" | "long" = "short"): string {
  const [y, m] = month.split("-").map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString(undefined, {
    month: style,
    year: style === "long" ? "numeric" : "2-digit",
  });
}
