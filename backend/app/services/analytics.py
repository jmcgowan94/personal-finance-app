"""Aggregations behind the dashboard.

Totals exclude transactions in "transfer" categories (moving money between your own
accounts, paying a card) so they are not counted as income or spending.
"""

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


def _apply(stmt: Select, f: Filters, *, exclude_transfers: bool = True) -> Select:
    stmt = stmt.where(Transaction.user_id == f.user_id)
    if f.date_from:
        stmt = stmt.where(Transaction.posted_date >= f.date_from)
    if f.date_to:
        stmt = stmt.where(Transaction.posted_date <= f.date_to)
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
    year = extract("year", Transaction.posted_date)
    month = extract("month", Transaction.posted_date)
    stmt = _apply(select(year, month, _income, _spend), f).group_by(year, month).order_by(year, month)
    out = []
    for y, m, income, spending in db.execute(stmt):
        income, spending = _money(income), _money(spending)
        out.append(
            {
                "month": f"{int(y):04d}-{int(m):02d}",
                "income": income,
                "spending": spending,
                "net": income - spending,
            }
        )
    return out


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
        select(Transaction.account_id, Transaction.posted_date, Transaction.balance),
        f,
        exclude_transfers=False,
    ).where(Transaction.balance.is_not(None)).order_by(
        Transaction.account_id, Transaction.posted_date, Transaction.upload_id, Transaction.sequence
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
