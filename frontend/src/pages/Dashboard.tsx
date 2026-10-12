import { Link, useNavigate } from "react-router-dom";

import { useBalance, useByCategory, useMe, useMonthly, useSummary } from "../api/hooks";
import { ChartCard } from "../components/ChartCard";
import { BalanceChart, CategoryChart, MonthlyChart } from "../components/charts";
import { FiltersBar } from "../components/FiltersBar";
import { useFilters } from "../lib/filters";
import { formatDate, formatMoney, formatMonth } from "../lib/format";

function StatTile({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="card">
      <div className="tile-label">{label}</div>
      <div className="tile-value">{value}</div>
      {sub && <div className="tile-sub">{sub}</div>}
    </div>
  );
}

export function Dashboard() {
  const { filters, ready } = useFilters();
  const navigate = useNavigate();
  const summary = useSummary(filters, ready);
  const monthly = useMonthly(filters, ready);
  const byCategory = useByCategory(filters, ready);
  const balance = useBalance(filters, ready);
  const { data: me } = useMe();
  // Greets by first name (from Account Information); empty until loaded so it doesn't flicker.
  const greeting = me ? `Hi ${me.first_name ?? "there"}` : "\u00a0";

  if (summary.isError) return <p className="error">Could not load data: {summary.error.message}</p>;

  const s = summary.data;
  const isEmpty = s && s.transaction_count === 0 && filters.range === "all" && !filters.accountId;

  return (
    <>
      <div className="page-header">
        <h1>{greeting}</h1>
        <FiltersBar />
      </div>

      {isEmpty ? (
        <div className="card empty">
          <h2>No transactions yet</h2>
          <p>
            <Link to="/import">Import a bank statement CSV</Link> to see your charts.
          </p>
          <p className="muted">
            Just exploring? Run <code>make seed-demo</code> to load sample data.
          </p>
        </div>
      ) : (
        <>
          <div className="tiles">
            <StatTile label="Income" value={s ? formatMoney(s.income) : "–"} />
            <StatTile label="Spending" value={s ? formatMoney(s.spending) : "–"} sub="Excludes transfers" />
            <StatTile
              label="Net"
              value={s ? formatMoney(s.net) : "–"}
              sub={s ? `${s.transaction_count.toLocaleString()} transactions` : undefined}
            />
          </div>

          <div className="stack">
            <ChartCard
              title="Income vs. spending"
              subtitle="Per month, excluding transfers between accounts"
              table={
                <table>
                  <thead>
                    <tr>
                      <th>Month</th>
                      <th className="num">Income</th>
                      <th className="num">Spending</th>
                      <th className="num">Net</th>
                    </tr>
                  </thead>
                  <tbody>
                    {monthly.data?.map((m) => (
                      <tr key={m.month}>
                        <td>{formatMonth(m.month, "long")}</td>
                        <td className="num">{formatMoney(m.income)}</td>
                        <td className="num">{formatMoney(m.spending)}</td>
                        <td className="num">{formatMoney(m.net)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              }
            >
              <MonthlyChart data={monthly.data ?? []} />
            </ChartCard>

            <div className="grid-2">
              <ChartCard
                title="Spending by category"
                subtitle="Select a bar to see its transactions"
                table={
                  <table>
                    <thead>
                      <tr>
                        <th>Category</th>
                        <th className="num">Spending</th>
                      </tr>
                    </thead>
                    <tbody>
                      {byCategory.data?.map((c) => (
                        <tr key={c.category}>
                          <td>{c.category}</td>
                          <td className="num">{formatMoney(c.spending)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                }
              >
                {byCategory.data?.length ? (
                  <CategoryChart
                    data={byCategory.data}
                    onSelect={(c) => navigate(`/transactions?category=${c.category_id ?? 0}`)}
                  />
                ) : (
                  <p className="muted">No spending in this period.</p>
                )}
              </ChartCard>

              <ChartCard
                title="Balance"
                subtitle="End-of-day balance from your statements"
                table={
                  <table>
                    <thead>
                      <tr>
                        <th>Account</th>
                        <th>Date</th>
                        <th className="num">Balance</th>
                      </tr>
                    </thead>
                    <tbody>
                      {balance.data?.flatMap((s) =>
                        s.points.map((p) => (
                          <tr key={`${s.account_id}-${p.date}`}>
                            <td>{s.account}</td>
                            <td className="date">{formatDate(p.date)}</td>
                            <td className="num">{formatMoney(p.balance)}</td>
                          </tr>
                        )),
                      )}
                    </tbody>
                  </table>
                }
              >
                {balance.data?.length ? (
                  <BalanceChart series={balance.data} />
                ) : (
                  <p className="muted">No balance information in these statements (credit card exports don't include one).</p>
                )}
              </ChartCard>
            </div>
          </div>
        </>
      )}
    </>
  );
}
