"""Generate synthetic Chase-style statements and import them for the local user.

    uv run python -m app.scripts.seed_demo            # import demo data
    uv run python -m app.scripts.seed_demo --out DIR  # only write the CSVs

All names and amounts are made up. Re-running is safe: duplicates are skipped.
"""

import argparse
import calendar
import csv
import io
import random
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from app.auth import get_or_create_user
from app.config import get_settings
from app.db import SessionLocal
from app.models import Account
from app.services.ingest import import_statement
from app.storage import get_storage

CHECKING_HEADERS = ["Details", "Posting Date", "Description", "Amount", "Type", "Balance", "Check or Slip #"]
CREDIT_HEADERS = ["Transaction Date", "Post Date", "Description", "Category", "Type", "Amount", "Memo"]

CARD_MERCHANTS = [
    ("WHOLEFDS MKT 10234", "Groceries", (40, 140), 5),
    ("TRADER JOE S #552", "Groceries", (25, 90), 4),
    ("DOORDASH*THAI PLACE", "Food & Drink", (22, 55), 3),
    ("STARBUCKS STORE 1187", "Food & Drink", (4, 9), 8),
    ("CHIPOTLE 2291", "Food & Drink", (11, 18), 3),
    ("UBER TRIP HELP.UBER.COM", "Travel", (9, 32), 4),
    ("SHELL OIL 57444", "Gas", (35, 60), 2),
    ("AMAZON MKTPL*2K4L9", "Shopping", (12, 120), 4),
    ("TARGET 00012345", "Shopping", (20, 90), 2),
    ("CVS/PHARMACY #0921", "Health & Wellness", (8, 40), 1),
    ("LOCAL HARDWARE CO", "Home", (15, 80), 1),
]
SUBSCRIPTIONS = [("NETFLIX.COM", Decimal("15.49"), 7), ("SPOTIFY USA", Decimal("11.99"), 12)]


def month_starts(months: int) -> list[date]:
    today = date.today().replace(day=1)
    starts = []
    for i in range(months, 0, -1):
        y, m = divmod(today.month - 1 - i, 12)
        starts.append(date(today.year + y, m + 1, 1))
    return starts


def money(rng: random.Random, low: float, high: float) -> Decimal:
    return Decimal(str(round(rng.uniform(low, high), 2)))


def to_csv(headers: list[str], rows: list[list]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)
    return buf.getvalue()


def generate(months: int = 6, seed: int = 42) -> list[tuple[str, str, str]]:
    """Return (filename, account kind, csv text) for each statement."""
    rng = random.Random(seed)
    files = []
    balance = Decimal("3200.00")
    for start in month_starts(months):
        last_day = calendar.monthrange(start.year, start.month)[1]
        end = start.replace(day=last_day)

        card: list[tuple[date, str, str, Decimal]] = []
        for desc, cat, (low, high), per_month in CARD_MERCHANTS:
            for _ in range(rng.randint(max(0, per_month - 1), per_month + 1)):
                card.append((start + timedelta(days=rng.randrange(last_day)), desc, cat, -money(rng, low, high)))
        for desc, amount, day in SUBSCRIPTIONS:
            card.append((start.replace(day=day), desc, "Entertainment", -amount))
        card_total = -sum(a for *_, a in card)
        card.sort()

        checking: list[tuple[date, str, str, Decimal]] = [
            (start.replace(day=1), "CITY APARTMENTS RENT", "ACH_DEBIT", Decimal("-1650.00")),
            (start.replace(day=1), "ACME CORP PAYROLL PPD ID: 9000000001", "ACH_CREDIT", Decimal("2850.00")),
            (start.replace(day=15), "ACME CORP PAYROLL PPD ID: 9000000001", "ACH_CREDIT", Decimal("2850.00")),
            (start.replace(day=8), "CITY POWER ELECTRIC", "ACH_DEBIT", -money(rng, 60, 140)),
            (start.replace(day=12), "XFINITY INTERNET", "ACH_DEBIT", Decimal("-70.00")),
            (start.replace(day=20), "ONLINE TRANSFER TO SAV XXXX0000", "ACCT_XFER", Decimal("-600.00")),
            (start.replace(day=22), "CHASE CREDIT CRD AUTOPAY", "ACH_DEBIT", -card_total),
            (start + timedelta(days=rng.randrange(last_day)), "ATM WITHDRAWAL 000123 MAIN ST", "ATM", Decimal("-80.00")),
        ]
        checking.sort(key=lambda r: r[0])
        rows = []
        for day, desc, kind, amount in checking:
            balance += amount
            details = "CREDIT" if amount > 0 else "DEBIT"
            rows.append([details, day.strftime("%m/%d/%Y"), desc, f"{amount:.2f}", kind, f"{balance:.2f}", ""])
        rows.reverse()  # Chase exports newest first
        stamp = end.strftime("%Y%m%d")
        files.append((f"DemoChecking_Activity_{stamp}.csv", "checking", to_csv(CHECKING_HEADERS, rows)))

        credit_rows = [
            [d.strftime("%m/%d/%Y"), min(d + timedelta(days=1), end).strftime("%m/%d/%Y"), desc, cat, "Sale", f"{a:.2f}", ""]
            for d, desc, cat, a in card
        ]
        credit_rows.append(
            [end.strftime("%m/%d/%Y"), end.strftime("%m/%d/%Y"), "Payment Thank You-Mobile", "", "Payment", f"{card_total:.2f}", ""]
        )
        credit_rows.reverse()
        files.append((f"DemoCard_Activity_{stamp}.csv", "credit", to_csv(CREDIT_HEADERS, credit_rows)))
    return files


def seed(files: list[tuple[str, str, str]]) -> None:
    settings = get_settings()
    storage = get_storage()
    with SessionLocal() as db:
        user = get_or_create_user(db, settings.local_user_subject)
        accounts = {}
        for name, kind in (("Demo Checking", "checking"), ("Demo Credit Card", "credit")):
            account = db.scalar(select(Account).where(Account.user_id == user.id, Account.name == name))
            if account is None:
                account = Account(user_id=user.id, name=name, institution="Chase", account_type=kind)
                db.add(account)
                db.commit()
            accounts[kind] = account
        for filename, kind, text in files:
            upload = import_statement(
                db, user_id=user.id, account=accounts[kind], filename=filename,
                data=text.encode(), storage=storage,
            )
            print(f"{filename}: {upload.rows_imported} imported, {upload.rows_duplicate} duplicates")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--months", type=int, default=6)
    parser.add_argument("--out", type=Path, help="write CSVs to this directory instead of importing")
    args = parser.parse_args()
    files = generate(args.months)
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        for filename, _, text in files:
            (args.out / filename).write_text(text)
        print(f"Wrote {len(files)} files to {args.out}")
    else:
        seed(files)


if __name__ == "__main__":
    main()
