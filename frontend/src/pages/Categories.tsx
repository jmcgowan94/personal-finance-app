import { useState } from "react";

import {
  useApplyRules,
  useCategories,
  useCreateCategory,
  useCreateRule,
  useDeleteCategory,
  useDeleteRule,
  useRules,
  useUpdateCategory,
} from "../api/hooks";
import type { Category, CategoryKind, CategoryRule, MatchType } from "../api/types";

const KIND_LABEL: Record<CategoryKind, string> = { expense: "Expense", income: "Income", transfer: "Transfer" };

function AddRuleForm({ category }: { category: Category }) {
  const [pattern, setPattern] = useState("");
  const [matchType, setMatchType] = useState<MatchType>("contains");
  const create = useCreateRule();
  return (
    <form
      className="form-row"
      style={{ marginTop: 8 }}
      onSubmit={(e) => {
        e.preventDefault();
        create.mutate(
          { category_id: category.id, pattern: pattern.trim(), match_type: matchType, priority: 0 },
          { onSuccess: () => setPattern("") },
        );
      }}
    >
      <input
        type="text"
        aria-label={`New rule for ${category.name}`}
        placeholder={matchType === "regex" ? "Regular expression" : "e.g. NETFLIX"}
        value={pattern}
        onChange={(e) => setPattern(e.target.value)}
      />
      <select aria-label="Match type" value={matchType} onChange={(e) => setMatchType(e.target.value as MatchType)}>
        <option value="contains">contains</option>
        <option value="regex">regex</option>
      </select>
      <button type="submit" className="small" disabled={!pattern.trim() || create.isPending}>
        Add rule
      </button>
      {create.isError && <span className="error">{create.error.message}</span>}
    </form>
  );
}

function CategoryRow({ category, rules }: { category: Category; rules: CategoryRule[] }) {
  const update = useUpdateCategory();
  const remove = useDeleteCategory();
  const deleteRule = useDeleteRule();
  const [confirming, setConfirming] = useState(false);
  return (
    <div className="category-row">
      <div className="category-row-head">
        <h2>{category.name}</h2>
        <select
          aria-label={`Kind of ${category.name}`}
          value={category.kind}
          onChange={(e) => update.mutate({ id: category.id, kind: e.target.value as CategoryKind })}
        >
          {Object.entries(KIND_LABEL).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <span style={{ flex: 1 }} />
        {confirming ? (
          <>
            <button className="small danger" onClick={() => remove.mutate(category.id)}>
              Delete category and its rules
            </button>
            <button className="small" onClick={() => setConfirming(false)}>
              Cancel
            </button>
          </>
        ) : (
          <button className="small" onClick={() => setConfirming(true)}>
            Delete
          </button>
        )}
      </div>
      <div className="rule-list">
        {rules.length === 0 && <span className="muted">No rules. Transactions are only assigned by hand.</span>}
        {rules.map((r) => (
          <span className="rule-chip" key={r.id}>
            {r.match_type === "regex" ? <code>/{r.pattern}/</code> : r.pattern}
            <button aria-label={`Remove rule ${r.pattern}`} onClick={() => deleteRule.mutate(r.id)}>
              ×
            </button>
          </span>
        ))}
      </div>
      <AddRuleForm category={category} />
    </div>
  );
}

export function Categories() {
  const { data: categories = [] } = useCategories();
  const { data: rules = [] } = useRules();
  const createCategory = useCreateCategory();
  const applyRules = useApplyRules();
  const [name, setName] = useState("");
  const [kind, setKind] = useState<CategoryKind>("expense");

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Categories</h1>
          <p className="muted" style={{ margin: "4px 0 0" }}>
            Rules match transaction descriptions (case-insensitive). The longest matching pattern wins. Transfers are
            left out of income and spending totals.
          </p>
        </div>
        <div className="toolbar">
          <button className="primary" disabled={applyRules.isPending} onClick={() => applyRules.mutate()}>
            Re-apply rules
          </button>
          {applyRules.isSuccess && <span className="success">{applyRules.data.updated} transactions updated</span>}
        </div>
      </div>

      <section className="card">
        <form
          className="form-row"
          onSubmit={(e) => {
            e.preventDefault();
            createCategory.mutate({ name: name.trim(), kind }, { onSuccess: () => setName("") });
          }}
        >
          <div className="field">
            <label htmlFor="cat-name">New category</label>
            <input id="cat-name" type="text" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="cat-kind">Kind</label>
            <select id="cat-kind" value={kind} onChange={(e) => setKind(e.target.value as CategoryKind)}>
              {Object.entries(KIND_LABEL).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          <button type="submit" disabled={!name.trim() || createCategory.isPending}>
            Add category
          </button>
          {createCategory.isError && <span className="error">{createCategory.error.message}</span>}
        </form>
      </section>

      <section className="card">
        {categories.map((c) => (
          <CategoryRow key={c.id} category={c} rules={rules.filter((r) => r.category_id === c.id)} />
        ))}
      </section>
    </>
  );
}
