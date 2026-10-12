"""Aggregations behind the dashboard.

Transactions are counted under their use date (which the user can adjust), except
balances, which follow the bank's posting date.

Totals exclude transactions in "transfer" categories (moving money between your own
accounts, paying a card) so they are not counted as income or spending.
"""

import calendar
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import Select, and_, case, extract, func, or_, select
from sqlalchemy.orm import Session

from app.models import Account, Category, Transaction

ZERO = Decimal("0.00")


@dataclass
class Filters:
    user_id: int
    date_from: date | None = None
    date_to: date | None = None
    account_id: int | None = None


def _apply(stmt: Select, f: Filters, *, exclude_transfers: bool = True, date_column=Transaction.use_date) -> Select:
    stmt = stmt.where(Transaction.user_id == f.user_id)
    if f.date_from:
        stmt = stmt.where(date_column >= f.date_from)
    if f.date_to:
        stmt = stmt.where(date_column <= f.date_to)
    if f.account_id:
        stmt = stmt.where(Transaction.account_id == f.account_id)
    if exclude_transfers:
        stmt = stmt.outerjoin(
            Category,
            and_(Category.id == Transaction.category_id, Category.user_id == f.user_id),
        ).where(or_(Category.id.is_(None), Category.kind != "transfer"))
    return stmt


_income = func.coalesce(func.sum(case((Transaction.amount > 0, Transaction.amount), else_=0)), 0)
_spend = func.coalesce(func.sum(case((Transaction.amount < 0, -Transaction.amount), else_=0)), 0)


def _money(value) -> Decimal:
    return Decimal(value or 0).quantize(Decimal("0.01"))


def summary(db: Session, f: Filters) -> dict:
    row = db.execute(_apply(select(_income, _spend, func.count(Transaction.id)), f)).one()
    income, spending = _money(row[0]), _money(row[1])
    return {
        "income": income,
        "spending": spending,
        "net": income - spending,
        "transaction_count": row[2],
    }


def monthly(db: Session, f: Filters) -> list[dict]:
    year = extract("year", Transaction.use_date)
    month = extract("month", Transaction.use_date)
    stmt = _apply(select(year, month, _income, _spend), f).group_by(year, month).order_by(year, month)
    rows = [(int(y), int(m), _money(income), _money(spending)) for y, m, income, spending in db.execute(stmt)]
    month_ends = [date(y, m, calendar.monthrange(y, m)[1]) for y, m, _, _ in rows]
    balances = _total_balances_at(db, f, month_ends)
    return [
        {
            "month": f"{y:04d}-{m:02d}",
            "income": income,
            "spending": spending,
            "net": income - spending,
            "end_balance": balance,
        }
        for (y, m, income, spending), balance in zip(rows, balances)
    ]


def _total_balances_at(db: Session, f: Filters, ends: list[date]) -> list[Decimal | None]:
    """Total balance across accounts at each of the (ascending) dates, as counted by
    use date.

    Starts from the bank's balance: each account's last reported balance on or before
    the date, so a month with no activity carries the previous balance forward. Then
    transactions whose use date was moved across the date are shifted to match:
    posted after it but counted on/before it -> added; posted on/before it but
    counted after it -> removed. So moving a paycheck into the right month moves it
    in the balance too, just as in the income totals.

    Accounts whose statements don't report a balance (e.g. credit cards) aren't
    included; None means no account had reported a balance yet.
    """
    if not ends:
        return []
    stmt = (
        select(Transaction.account_id, Transaction.posting_date, Transaction.balance)
        .where(
            Transaction.user_id == f.user_id,
            Transaction.balance.is_not(None),
            Transaction.posting_date <= ends[-1],
        )
        .order_by(Transaction.posting_date, Transaction.upload_id, Transaction.sequence)
    )
    if f.account_id:
        stmt = stmt.where(Transaction.account_id == f.account_id)
    rows = db.execute(stmt).all()

    # Transactions moved off their posting date, in accounts that report balances.
    moved_stmt = select(
        Transaction.account_id, Transaction.posting_date, Transaction.use_date, Transaction.amount
    ).where(
        Transaction.user_id == f.user_id,
        Transaction.use_date != Transaction.posting_date,
        Transaction.account_id.in_({r.account_id for r in rows}),
    )
    moved = db.execute(moved_stmt).all()

    latest: dict[int, Decimal] = {}
    totals: list[Decimal | None] = []
    i = 0
    for end in ends:
        while i < len(rows) and rows[i].posting_date <= end:
            latest[rows[i].account_id] = rows[i].balance
            i += 1
        if not latest:
            totals.append(None)
            continue
        shift = sum(
            (
                m.amount if m.use_date <= end < m.posting_date else -m.amount
                for m in moved
                if m.account_id in latest and (m.use_date <= end) != (m.posting_date <= end)
            ),
            Decimal(0),
        )
        totals.append(_money(sum(latest.values()) + shift))
    return totals


def by_category(db: Session, f: Filters) -> list[dict]:
    """Spending (money out) per category, largest first. Uncategorised is category None."""
    stmt = (
        _apply(select(Category.id, Category.name, _spend), f)
        .where(Transaction.amount < 0)
        .group_by(Category.id, Category.name)
    )
    rows = [
        {"category_id": cid, "category": name or "Uncategorized", "spending": _money(spend)}
        for cid, name, spend in db.execute(stmt)
    ]
    return sorted(rows, key=lambda r: r["spending"], reverse=True)


def balance_history(db: Session, f: Filters) -> list[dict]:
    """End-of-day balance per account, for accounts whose statements report a balance."""
    stmt = _apply(
        select(Transaction.account_id, Transaction.posting_date, Transaction.balance),
        f,
        exclude_transfers=False,
        date_column=Transaction.posting_date,
    ).where(Transaction.balance.is_not(None)).order_by(
        Transaction.account_id, Transaction.posting_date, Transaction.upload_id, Transaction.sequence
    )
    series: dict[int, dict[date, Decimal]] = {}
    for account_id, day, balance in db.execute(stmt):
        # Later rows overwrite earlier ones, leaving the end-of-day balance.
        series.setdefault(account_id, {})[day] = balance
    if not series:
        return []
    names = dict(
        db.execute(
            select(Account.id, Account.name).where(
                Account.user_id == f.user_id, Account.id.in_(series.keys())
            )
        ).all()
    )
    return [
        {
            "account_id": account_id,
            "account": names.get(account_id, ""),
            "points": [{"date": d, "balance": b} for d, b in points.items()],
        }
        for account_id, points in series.items()
    ]
