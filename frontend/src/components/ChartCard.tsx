import { useState, type ReactNode } from "react";

/** A chart with a title and a Chart/Table toggle, so every value is readable without colour. */
export function ChartCard({
  title,
  subtitle,
  table,
  children,
}: {
  title: string;
  subtitle?: string;
  table: ReactNode;
  children: ReactNode;
}) {
  const [view, setView] = useState<"chart" | "table">("chart");
  return (
    <section className="card">
      <div className="chart-head">
        <div>
          <h2>{title}</h2>
          {subtitle && <div className="chart-sub">{subtitle}</div>}
        </div>
        <div className="segmented" role="group" aria-label={`${title} view`}>
          <button aria-pressed={view === "chart"} onClick={() => setView("chart")}>
            Chart
          </button>
          <button aria-pressed={view === "table"} onClick={() => setView("table")}>
            Table
          </button>
        </div>
      </div>
      {view === "chart" ? children : <div className="table-wrap">{table}</div>}
    </section>
  );
}

export function ChartTooltip({ title, rows }: { title: string; rows: { label: string; value: string; color?: string }[] }) {
  return (
    <div className="tooltip">
      <div className="tooltip-title">{title}</div>
      {rows.map((row) => (
        <div className="tooltip-row" key={row.label}>
          <span>
            {row.color && <span className="legend-key" style={{ background: row.color }} />}
            {row.label}
          </span>
          <strong>{row.value}</strong>
        </div>
      ))}
    </div>
  );
}

export function Legend({ items }: { items: { label: string; color: string }[] }) {
  return (
    <div className="legend">
      {items.map((item) => (
        <span key={item.label}>
          <span className="legend-key" style={{ background: item.color }} />
          {item.label}
        </span>
      ))}
    </div>
  );
}
