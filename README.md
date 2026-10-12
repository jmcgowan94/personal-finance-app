# Personal Finance

A small app for visualizing the transactions in your bank-statement CSV exports.
Import your monthly statements and get:

- **Dashboard**: income, spending and net totals, income vs. spending per month, spending by category, and account balance over time.
- **Transactions**: a searchable, filterable list, where you can recategorize any transaction.
- **Categories**: keyword or regex rules that categorize transactions automatically.

Supported formats today: **Chase checking/savings** and **Chase credit card** CSV exports. Adding another bank takes one small file; see [Adding a bank format](#adding-a-bank-format).

Everything runs on your machine. Your statements and database live in `./data/`, which git ignores.

## Quick start

You need [uv](https://docs.astral.sh/uv/) (Python) and [Node.js](https://nodejs.org/) 20 or later.

```bash
git clone <this repo> && cd personal-finance-app
make setup        # install dependencies
make dev          # API on :8000, web app on http://localhost:5173
```

Open http://localhost:5173, go to **Import**, create an account (e.g. "Chase Checking") and drop in your CSV files.

To explore with made-up data first:

```bash
make seed-demo    # imports 6 months of synthetic statements
make demo-csvs    # or just write them to data/demo-statements/ to try the upload flow
```

### With Docker instead

If you have Docker, this runs the same app against Postgres (the database used in the cloud):

```bash
cp .env.example .env   # optional
docker compose up --build
```

### Without make

```bash
cd backend && uv sync && uv run alembic upgrade head && uv run uvicorn app.main:app --reload
cd frontend && npm install && npm run dev       # in a second terminal
```

## Getting your CSVs from Chase

In Chase online banking, open the account, choose **Download account activity**, pick **CSV** and a date range. Monthly files work well, but any range does. Overlapping files are fine because duplicates are detected and skipped.

## How it works

| | |
|---|---|
| `backend/` | Python 3.12, FastAPI, SQLAlchemy 2, Alembic. SQLite by default, Postgres in Docker or AWS. |
| `frontend/` | React, TypeScript and Vite, with TanStack Query and Recharts. |
| `data/` | Your local database and the raw uploaded files (git-ignored). |

Notes on the numbers:
- **Transfers** (categories of kind "Transfer", e.g. credit card payments and moves to savings) are left out of income and spending, so money isn't counted twice.
- **Income** is money in and **spending** is money out, both after excluding transfers. A refund therefore counts as money in.
- **Use Date vs. Posting Date.** Totals, charts and date filters use each transaction's **Use Date**, which starts as the bank's **Posting Date**. You can change it on the Transactions page, e.g. to count a paycheck paid early for a weekend in the month it was meant for. The month-end balance line on the Income vs. spending chart is shifted to match: a paycheck counted in June raises June's balance even if it posted July 1. The separate Balance chart (the bank's day-by-day balance) and duplicate detection always use the Posting Date.
- **Duplicates.** A transaction is identified by account, date, amount, description and balance (plus its position among identical same-day rows), so re-importing a statement never double-counts.
- **Deleting an import** removes the transactions it added.
- **Categories you set by hand** are marked "manual", and **Re-apply rules** leaves them alone.

Configuration is entirely through environment variables; see [.env.example](.env.example).

### Running the tests

```bash
make test         # backend pytest + frontend type-check
```

## Versions and releases

The app follows [semantic versioning](https://semver.org): **major.minor.patch**.

| Change | Bump | Command |
|---|---|---|
| Bug fixes only | patch: 0.2.0 → 0.2.1 | `make release-patch` |
| New features | minor: 0.2.1 → 0.3.0 | `make release-minor` |
| Breaking changes (e.g. data that older versions can't read) | major: 0.3.0 → 1.0.0 | `make release-major` |

The version stays below 1.0 until the hosted, multi-user version is live.

A release bumps the version in `backend/pyproject.toml` (the source of truth) and its mirrors, adds the commits since the last release to [CHANGELOG.md](CHANGELOG.md), commits, tags `vX.Y.Z` and pushes. Run it from an up-to-date `main` with no uncommitted changes.

The sidebar shows the version and commit the running server was started from (e.g. `v0.2.0 · 1a2b3c4`). If that's older than the latest release, restart the app.

## Adding a bank format

Create a parser in `backend/app/parsers/`, such as `mybank.py`:

```python
from app.parsers.base import ParsedTransaction, StatementParser, parse_money, parse_us_date, register

@register
class MyBankParser(StatementParser):
    name = "mybank_checking"
    label = "My Bank checking"
    institution = "My Bank"
    account_type = "checking"
    required_headers = frozenset({"Date", "Payee", "Amount"})   # used to auto-detect the file

    def parse_row(self, row: dict[str, str]) -> ParsedTransaction:
        return ParsedTransaction(
            posted_date=parse_us_date(row["Date"]),
            description=row["Payee"],
            amount=parse_money(row["Amount"]),   # negative = money out
        )
```

Then import it in `backend/app/parsers/__init__.py`, and add a small synthetic fixture and a test under `backend/tests/`. Never commit real statements.

## Built for multiple users and AWS

The app runs as a single local user today, but it is structured to become a hosted, multi-user web app:

- **Every row belongs to a user.** Each table has a `user_id`, and every query filters on it. Tests (`test_users_cannot_see_or_touch_each_others_data`) check that one user can't read or change another's data.
- **One place decides who the user is.** `get_current_user` in [backend/app/auth.py](backend/app/auth.py) returns the local user when `AUTH_MODE=local`. Switching to `AUTH_MODE=cognito` means implementing token verification there; nothing else changes.
- **Pluggable file storage.** Raw uploads go through [backend/app/storage.py](backend/app/storage.py): local disk now, S3 with `STORAGE_BACKEND=s3`. Keys are already shaped `users/<id>/uploads/...`.
- **Configuration only through environment variables**, and a stateless API, so the same container runs anywhere.
- **Database migrations** (Alembic) run the same way against SQLite and Postgres/RDS.

Suggested AWS setup:

| Piece | AWS service |
|---|---|
| Web app (`npm run build` output) | S3 + CloudFront |
| API (`backend/Dockerfile`) | App Runner or ECS Fargate, with CloudFront routing `/api/*` to it |
| Database | RDS for PostgreSQL (`DATABASE_URL`) |
| Uploaded files | S3 (`STORAGE_BACKEND=s3`, `S3_BUCKET`) |
| Sign-up and login | Cognito user pool (`AUTH_MODE=cognito`), with sign-in added to the frontend via `setTokenProvider` in `frontend/src/api/client.ts` |
| Secrets | Secrets Manager or SSM Parameter Store |

Remaining work for that move: implement Cognito token verification in `auth.py`, add a sign-in screen to the frontend, and write the infrastructure (e.g. AWS CDK or Terraform).
