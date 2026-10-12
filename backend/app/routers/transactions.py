from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import Category, Transaction, User
from app.schemas import TransactionOut, TransactionPage, TransactionPatch
from app.services.ownership import get_owned

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=TransactionPage)
def list_transactions(
    date_from: date | None = None,
    date_to: date | None = None,
    account_id: int | None = None,
    category_id: int | None = Query(None, description="Use 0 for uncategorised"),
    q: str | None = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Transaction).where(Transaction.user_id == user.id)
    if date_from:
        stmt = stmt.where(Transaction.posted_date >= date_from)
    if date_to:
        stmt = stmt.where(Transaction.posted_date <= date_to)
    if account_id:
        stmt = stmt.where(Transaction.account_id == account_id)
    if category_id == 0:
        stmt = stmt.where(Transaction.category_id.is_(None))
    elif category_id:
        stmt = stmt.where(Transaction.category_id == category_id)
    if q:
        stmt = stmt.where(Transaction.description.ilike(f"%{q}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(
        stmt.order_by(
            Transaction.posted_date.desc(),
            Transaction.upload_id.desc(),
            Transaction.sequence.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return TransactionPage(items=items, total=total, page=page, page_size=page_size)


@router.patch("/{transaction_id}", response_model=TransactionOut)
def update_transaction(
    transaction_id: int,
    body: TransactionPatch,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set a transaction's category by hand. Rules will no longer change it,
    unless the category is cleared (set to null)."""
    txn = get_owned(db, Transaction, transaction_id, user.id)
    if body.category_id is not None:
        get_owned(db, Category, body.category_id, user.id)
    txn.category_id = body.category_id
    txn.category_locked = body.category_id is not None
    db.commit()
    return txn
