import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { BalanceSeries, CategorySpend, MonthlyPoint } from "../api/types";
import { formatDate, formatMoney, formatMoneyCompact, formatMonth, toNumber } from "../lib/format";
import { ChartTooltip, Legend } from "./ChartCard";

const AXIS = { stroke: "var(--baseline)", tick: { fill: "var(--axis-text)", fontSize: 12 }, tickLine: false };
const GRID = { stroke: "var(--grid)", strokeDasharray: undefined };
const INCOME = "var(--series-1)";
const SPENDING = "var(--series-2)";

export function MonthlyChart({ data }: { data: MonthlyPoint[] }) {
  const rows = data.map((d) => ({ ...d, income: toNumber(d.income), spending: toNumber(d.spending) }));
  return (
    <>
      <Legend
        items={[
          { label: "Income", color: INCOME },
          { label: "Spending", color: SPENDING },
        ]}
      />
      <div className="chart-body">
        <ResponsiveContainer>
          <BarChart data={rows} barGap={2} barSize={rows.length > 12 ? 8 : 20} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid vertical={false} {...GRID} />
            <XAxis dataKey="month" tickFormatter={(m) => formatMonth(m)} {...AXIS} />
            <YAxis tickFormatter={formatMoneyCompact} width={56} axisLine={false} {...AXIS} />
            <Tooltip
              cursor={{ fill: "var(--hover)" }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const p = payload[0].payload as MonthlyPoint & { income: number; spending: number };
                return (
                  <ChartTooltip
                    title={formatMonth(p.month, "long")}
                    rows={[
                      { label: "Income", value: formatMoney(p.income), color: INCOME },
                      { label: "Spending", value: formatMoney(p.spending), color: SPENDING },
                      { label: "Net", value: formatMoney(p.net) },
                    ]}
                  />
                );
              }}
            />
            <Bar isAnimationActive={false} dataKey="income" name="Income" fill={INCOME} radius={[4, 4, 0, 0]} />
            <Bar isAnimationActive={false} dataKey="spending" name="Spending" fill={SPENDING} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </>
  );
}

export function CategoryChart({ data, onSelect }: { data: CategorySpend[]; onSelect?: (c: CategorySpend) => void }) {
  const rows = data.map((d) => ({ ...d, spending: toNumber(d.spending) }));
  const height = Math.max(160, rows.length * 34 + 24);
  return (
    <div style={{ height }}>
      <ResponsiveContainer>
        <BarChart data={rows} layout="vertical" margin={{ top: 0, right: 72, left: 0, bottom: 0 }}>
          <CartesianGrid horizontal={false} {...GRID} />
          <XAxis type="number" tickFormatter={formatMoneyCompact} axisLine={false} {...AXIS} />
          <YAxis type="category" dataKey="category" width={110} axisLine={false} {...AXIS} />
          <Tooltip
            cursor={{ fill: "var(--hover)" }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const p = payload[0].payload as CategorySpend & { spending: number };
              return <ChartTooltip title={p.category} rows={[{ label: "Spending", value: formatMoney(p.spending) }]} />;
            }}
          />
          <Bar
            isAnimationActive={false}
            dataKey="spending"
            fill="var(--series-1)"
            maxBarSize={24}
            radius={[0, 4, 4, 0]}
            cursor={onSelect ? "pointer" : undefined}
            onClick={(entry) => onSelect?.(entry.payload as CategorySpend)}
          >
            <LabelList
              dataKey="spending"
              position="right"
              formatter={(v) => formatMoneyCompact(Number(v))}
              style={{ fill: "var(--text-secondary)", fontSize: 12 }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

const ACCOUNT_COLORS = ["var(--series-1)", "var(--series-2)", "var(--series-3)"];

/** Balance over time. Accounts are merged onto one date axis; each keeps its last known value. */
export function BalanceChart({ series }: { series: BalanceSeries[] }) {
  const shown = series.slice(0, ACCOUNT_COLORS.length);
  const byDate = new Map<string, Record<string, number | string>>();
  for (const s of shown) {
    for (const p of s.points) {
      const row = byDate.get(p.date) ?? { date: p.date };
      row[`a${s.account_id}`] = toNumber(p.balance);
      byDate.set(p.date, row);
    }
  }
  const rows = [...byDate.values()].sort((a, b) => String(a.date).localeCompare(String(b.date)));
  const last: Record<string, number> = {};
  for (const row of rows) {
    for (const s of shown) {
      const key = `a${s.account_id}`;
      if (row[key] === undefined && last[key] !== undefined) row[key] = last[key];
      if (row[key] !== undefined) last[key] = row[key] as number;
    }
  }
  const colorOf = (i: number) => ACCOUNT_COLORS[i];

  return (
    <>
      {shown.length > 1 && <Legend items={shown.map((s, i) => ({ label: s.account, color: colorOf(i) }))} />}
      <div className="chart-body">
        <ResponsiveContainer>
          <AreaChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid vertical={false} {...GRID} />
            <XAxis
              dataKey="date"
              tickFormatter={(d: string) => formatMonth(d.slice(0, 7))}
              minTickGap={32}
              {...AXIS}
            />
            <YAxis tickFormatter={formatMoneyCompact} width={56} axisLine={false} domain={["auto", "auto"]} {...AXIS} />
            <Tooltip
              cursor={{ stroke: "var(--baseline)" }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const row = payload[0].payload as Record<string, number | string>;
                return (
                  <ChartTooltip
                    title={formatDate(String(row.date))}
                    rows={shown
                      .map((s, i) => ({ s, i, v: row[`a${s.account_id}`] }))
                      .filter(({ v }) => v !== undefined)
                      .map(({ s, i, v }) => ({
                        label: s.account,
                        value: formatMoney(v as number),
                        color: shown.length > 1 ? colorOf(i) : undefined,
                      }))}
                  />
                );
              }}
            />
            {shown.map((s, i) => (
              <Area
                isAnimationActive={false}
                key={s.account_id}
                type="linear"
                dataKey={`a${s.account_id}`}
                name={s.account}
                stroke={colorOf(i)}
                strokeWidth={2}
                fill={colorOf(i)}
                fillOpacity={0.1}
                dot={false}
                activeDot={{ r: 4, strokeWidth: 2, stroke: "var(--surface)" }}
                connectNulls
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </>
  );
}
