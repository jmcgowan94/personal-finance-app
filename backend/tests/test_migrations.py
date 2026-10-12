"""Migrations must never lose data.

Runs the real Alembic migrations (in a subprocess, against a throwaway SQLite file)
on a database that already holds data, upgrading one revision at a time.
"""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
TABLES = ["users", "accounts", "uploads", "categories", "category_rules", "transactions"]


def alembic(db: Path, *args: str) -> None:
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db}"}
    subprocess.run(
        [sys.executable, "-m", "alembic", *args], cwd=BACKEND, env=env, check=True, capture_output=True
    )


def revisions() -> list[str]:
    return sorted(p.name.split("_", 1)[0] for p in (BACKEND / "alembic" / "versions").glob("[0-9]*_*.py"))


def counts(db: Path) -> dict[str, int]:
    with sqlite3.connect(db) as conn:
        return {t: conn.execute(f"select count(*) from {t}").fetchone()[0] for t in TABLES}


def test_upgrading_a_populated_database_keeps_every_row(tmp_path):
    db = tmp_path / "app.db"
    alembic(db, "upgrade", "0001")
    with sqlite3.connect(db) as conn:
        conn.executescript(
            """
            insert into users (id, auth_subject) values (1, 'local');
            insert into accounts (id, user_id, name, institution, account_type) values (1, 1, 'Checking', 'Chase', 'checking');
            insert into uploads (id, user_id, account_id, filename, storage_key, parser_name,
                                 rows_total, rows_imported, rows_duplicate, rows_error)
                values (1, 1, 1, 'a.csv', 'k', 'chase_checking', 1, 1, 0, 0);
            insert into categories (id, user_id, name, kind) values (1, 1, 'Dining', 'expense');
            insert into category_rules (id, user_id, category_id, pattern, match_type, priority)
                values (1, 1, 1, 'CAFE', 'contains', 0);
            insert into transactions (id, user_id, account_id, upload_id, posted_date, sequence, description,
                                      amount, category_id, category_locked, dedupe_hash)
                values (1, 1, 1, 1, '2026-01-01', 0, 'CAFE', -4.5, 1, 0, 'h');
            """
        )
    before = counts(db)
    assert all(before.values())

    for rev in revisions()[1:]:
        alembic(db, "upgrade", rev)
        assert counts(db) == before, f"rows lost upgrading to {rev}"

    with sqlite3.connect(db) as conn:
        # Use date starts out equal to the bank's posting date.
        assert conn.execute("select posting_date, use_date from transactions").fetchall() == [("2026-01-01", "2026-01-01")]

    alembic(db, "downgrade", "0001")
    assert counts(db) == before, "rows lost downgrading"
