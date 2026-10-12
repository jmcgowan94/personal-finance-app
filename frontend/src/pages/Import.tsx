import { useRef, useState, type DragEvent } from "react";

import { useAccounts, useCreateAccount, useDeleteUpload, useParsers, useUploads, useUploadStatement } from "../api/hooks";
import type { AccountType } from "../api/types";
import { formatDate } from "../lib/format";

type Result = { file: string; ok: boolean; message: string };

function NewAccountForm({ onCreated }: { onCreated: (id: number) => void }) {
  const [name, setName] = useState("");
  const [type, setType] = useState<AccountType>("checking");
  const create = useCreateAccount();
  return (
    <form
      className="form-row"
      onSubmit={(e) => {
        e.preventDefault();
        create.mutate(
          { name: name.trim(), account_type: type },
          {
            onSuccess: (a) => {
              setName("");
              onCreated(a.id);
            },
          },
        );
      }}
    >
      <div className="field">
        <label htmlFor="acct-name">New account name</label>
        <input id="acct-name" type="text" placeholder="e.g. Chase Checking" value={name} onChange={(e) => setName(e.target.value)} />
      </div>
      <div className="field">
        <label htmlFor="acct-type">Type</label>
        <select id="acct-type" value={type} onChange={(e) => setType(e.target.value as AccountType)}>
          <option value="checking">Checking</option>
          <option value="savings">Savings</option>
          <option value="credit">Credit card</option>
          <option value="other">Other</option>
        </select>
      </div>
      <button type="submit" disabled={!name.trim() || create.isPending}>
        Add account
      </button>
      {create.isError && <span className="error">{create.error.message}</span>}
    </form>
  );
}

export function Import() {
  const { data: accounts = [] } = useAccounts();
  const { data: uploads = [] } = useUploads();
  const { data: parsers = [] } = useParsers();
  const uploadStatement = useUploadStatement();
  const deleteUpload = useDeleteUpload();
  const [accountId, setAccountId] = useState<number | null>(null);
  const [results, setResults] = useState<Result[]>([]);
  const [busy, setBusy] = useState(false);
  const [over, setOver] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const selected = accountId ?? accounts[0]?.id ?? null;
  const accountName = new Map(accounts.map((a) => [a.id, a.name]));

  async function handleFiles(files: FileList | File[]) {
    if (!selected) return;
    setBusy(true);
    const out: Result[] = [];
    for (const file of Array.from(files)) {
      try {
        const u = await uploadStatement.mutateAsync({ file, accountId: selected });
        const parts = [`${u.rows_imported} imported`];
        if (u.rows_duplicate) parts.push(`${u.rows_duplicate} already imported`);
        if (u.rows_error) parts.push(`${u.rows_error} unreadable rows`);
        out.push({ file: file.name, ok: true, message: parts.join(", ") });
      } catch (err) {
        out.push({ file: file.name, ok: false, message: (err as Error).message });
      }
      setResults([...out]);
    }
    setBusy(false);
    if (inputRef.current) inputRef.current.value = "";
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setOver(false);
    if (e.dataTransfer.files.length) void handleFiles(e.dataTransfer.files);
  }

  return (
    <>
      <div className="page-header">
        <h1>Import statements</h1>
      </div>

      <section className="card">
        <h2>1. Choose the account</h2>
        <div className="form-row" style={{ marginTop: 12 }}>
          {accounts.length > 0 && (
            <div className="field">
              <label htmlFor="account">Account</label>
              <select id="account" value={selected ?? ""} onChange={(e) => setAccountId(Number(e.target.value))}>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
        <div style={{ marginTop: 12 }}>
          <NewAccountForm onCreated={setAccountId} />
        </div>
      </section>

      <section className="card">
        <h2>2. Add CSV files</h2>
        <p className="muted">
          Supported formats: {parsers.map((p) => p.label).join(", ")}. Re-importing overlapping statements is safe;
          transactions already imported are skipped.
        </p>
        <div
          className={`dropzone ${over ? "over" : ""}`}
          role="button"
          tabIndex={0}
          aria-disabled={!selected || busy}
          onClick={() => selected && inputRef.current?.click()}
          onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && selected && inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setOver(true);
          }}
          onDragLeave={() => setOver(false)}
          onDrop={onDrop}
        >
          {!selected
            ? "Add an account first"
            : busy
              ? "Importing…"
              : `Drop CSV files here, or click to choose (into ${accountName.get(selected)})`}
        </div>
        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          multiple
          hidden
          onChange={(e) => e.target.files && void handleFiles(e.target.files)}
        />
        {results.length > 0 && (
          <ul>
            {results.map((r, i) => (
              <li key={i} className={r.ok ? "success" : "error"}>
                <strong>{r.file}</strong>: {r.message}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card">
        <h2>Import history</h2>
        {uploads.length === 0 ? (
          <p className="muted">Nothing imported yet.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>File</th>
                  <th>Account</th>
                  <th>Imported on</th>
                  <th className="num">New</th>
                  <th className="num">Skipped</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {uploads.map((u) => (
                  <tr key={u.id}>
                    <td>{u.filename}</td>
                    <td className="muted">{accountName.get(u.account_id)}</td>
                    <td className="date">{formatDate(u.created_at.slice(0, 10))}</td>
                    <td className="num">{u.rows_imported}</td>
                    <td className="num">{u.rows_duplicate + u.rows_error}</td>
                    <td className="num">
                      {confirmDelete === u.id ? (
                        <>
                          <button
                            className="small danger"
                            onClick={() => deleteUpload.mutate(u.id, { onSettled: () => setConfirmDelete(null) })}
                          >
                            Delete {u.rows_imported} transactions
                          </button>{" "}
                          <button className="small" onClick={() => setConfirmDelete(null)}>
                            Cancel
                          </button>
                        </>
                      ) : (
                        <button className="small" onClick={() => setConfirmDelete(u.id)}>
                          Delete
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
