import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { useAccounts, useCategories, useTransactions, useUpdateTransaction } from "../api/hooks";
import type { Transaction } from "../api/types";
import { FiltersBar } from "../components/FiltersBar";
import { rangeStart, useFilters } from "../lib/filters";
import { formatDate, formatMoney, toNumber } from "../lib/format";

const PAGE_SIZE = 50;

export function Transactions() {
  const { filters, ready } = useFilters();
  const [searchParams, setSearchParams] = useSearchParams();
  const categoryParam = searchParams.get("category");
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  // Pages run oldest -> newest, but the API pages newest-first. Track how many
  // pages back from the newest we are (0 = most recent, where the page opens).
  const [stepsBack, setStepsBack] = useState(0);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(search.trim()), 250);
    return () => clearTimeout(t);
  }, [search]);
  useEffect(() => setStepsBack(0), [debounced, categoryParam, filters]);

  const { data: accounts = [] } = useAccounts();
  const { data: categories = [] } = useCategories();
  const accountName = useMemo(() => new Map(accounts.map((a) => [a.id, a.name])), [accounts]);
  const updateTxn = useUpdateTransaction();

  const { data, isError, error, isFetching } = useTransactions({
    date_from: rangeStart(filters.range),
    account_id: filters.accountId ?? undefined,
    category_id: categoryParam === null ? undefined : Number(categoryParam),
    q: debounced || undefined,
    page: stepsBack + 1,
    page_size: PAGE_SIZE,
  }, ready);

  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;
  const page = pages - stepsBack; // chronological page number shown to the user
  // Oldest at the top, so time runs down the page and forward through the pages.
  const rows = data ? [...data.items].reverse() : [];

  return (
    <>
      <div className="page-header">
        <h1>Transactions</h1>
        <div className="toolbar">
          <input
            type="search"
            placeholder="Search descriptions"
            aria-label="Search descriptions"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <select
            aria-label="Category"
            value={categoryParam ?? ""}
            onChange={(e) => {
              const next = new URLSearchParams(searchParams);
              if (e.target.value === "") next.delete("category");
              else next.set("category", e.target.value);
              setSearchParams(next);
            }}
          >
            <option value="">All categories</option>
            <option value="0">Uncategorized</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          <FiltersBar />
        </div>
      </div>

      <section className="card">
        {isError && <p className="error">Could not load transactions: {error.message}</p>}
        {updateTxn.isError && <p className="error">{updateTxn.error.message}</p>}
        <div className="table-wrap" style={{ opacity: isFetching ? 0.7 : 1 }}>
          <table>
            <thead>
              <tr>
                <th>Posting Date</th>
                <th>
                  <span title="The date this transaction counts under in totals and charts. Starts as the posting date.">
                    Use Date
                  </span>
                </th>
                <th>Description</th>
                <th>Account</th>
                <th>Category</th>
                <th className="num">Amount</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((t) => (
                <tr key={t.id}>
                  <td className="date">{formatDate(t.posting_date)}</td>
                  <td>
                    <UseDateCell txn={t} onSave={(useDate) => updateTxn.mutate({ id: t.id, use_date: useDate })} />
                  </td>
                  <td className="desc">
                    {t.description}
                    {t.bank_category && <small>Bank category: {t.bank_category}</small>}
                  </td>
                  <td className="muted">{accountName.get(t.account_id)}</td>
                  <td>
                    <select
                      aria-label={`Category for ${t.description}`}
                      value={t.category_id ?? ""}
                      onChange={(e) =>
                        updateTxn.mutate({ id: t.id, category_id: e.target.value ? Number(e.target.value) : null })
                      }
                    >
                      <option value="">Uncategorized</option>
                      {categories.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name}
                        </option>
                      ))}
                    </select>{" "}
                    {t.category_locked && (
                      <span className="badge" title="Set by you; rules won't change it">
                        manual
                      </span>
                    )}
                  </td>
                  <td className={`num ${toNumber(t.amount) > 0 ? "amount-in" : ""}`}>{formatMoney(t.amount)}</td>
                </tr>
              ))}
              {data?.items.length === 0 && (
                <tr>
                  <td colSpan={6} className="muted" style={{ textAlign: "center", padding: 32 }}>
                    No transactions match these filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {data && data.total > 0 && (
          <div className="pager">
            <span>
              {data.total.toLocaleString()} transactions · page {page} of {pages}
            </span>
            <div className="toolbar">
              <button className="small" disabled={page <= 1} onClick={() => setStepsBack(stepsBack + 1)}>
                Previous
              </button>
              <button className="small" disabled={stepsBack === 0} onClick={() => setStepsBack(stepsBack - 1)}>
                Next
              </button>
            </div>
          </div>
        )}
      </section>
    </>
  );
}

const USE_DATE_SAVE_DELAY_MS = 800;

/**
 * Editable use date. Saves once the user stops editing: after a short pause, on
 * leaving the field, or on Enter. That way a date being typed digit by digit (which
 * passes through other valid dates) is saved once, not at every step.
 */
function UseDateCell({ txn, onSave }: { txn: Transaction; onSave: (useDate: string | null) => void }) {
  const [value, setValue] = useState(txn.use_date);
  const timer = useRef<number | undefined>(undefined);
  const latest = useRef({ value, txn, onSave });
  latest.current = { value, txn, onSave };
  useEffect(() => setValue(txn.use_date), [txn.use_date]);
  const adjusted = txn.use_date !== txn.posting_date;

  // Save the current value if it's a complete, changed date.
  const flush = () => {
    window.clearTimeout(timer.current);
    const { value: v, txn: t, onSave: save } = latest.current;
    if (v && Number(v.slice(0, 4)) >= 1900 && v !== t.use_date) save(v);
  };
  useEffect(() => flush, []); // don't lose a pending edit if the row goes away

  return (
    <span className="use-date">
      <input
        type="date"
        className={adjusted ? "adjusted" : undefined}
        aria-label={`Use date for ${txn.description}`}
        value={value}
        onChange={(e) => {
          setValue(e.target.value);
          window.clearTimeout(timer.current);
          timer.current = window.setTimeout(flush, USE_DATE_SAVE_DELAY_MS);
        }}
        onBlur={() => {
          flush();
          if (!value) setValue(txn.use_date); // cleared field: put the saved date back
        }}
        onKeyDown={(e) => e.key === "Enter" && flush()}
      />
      {adjusted && (
        <button
          type="button"
          className="link small"
          title={`Reset to the posting date (${formatDate(txn.posting_date)})`}
          onClick={() => onSave(null)}
        >
          Reset
        </button>
      )}
    </span>
  );
}
