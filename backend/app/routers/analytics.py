from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import User
from app.schemas import BalanceSeries, CategorySpend, MonthlyPoint, Summary
from app.services import analytics

router = APIRouter(prefix="/analytics", tags=["analytics"])


def filters(
    date_from: date | None = None,
    date_to: date | None = None,
    account_id: int | None = None,
    user: User = Depends(get_current_user),
) -> analytics.Filters:
    return analytics.Filters(user.id, date_from, date_to, account_id)


@router.get("/summary", response_model=Summary)
def summary(f: analytics.Filters = Depends(filters), db: Session = Depends(get_db)):
    return analytics.summary(db, f)


@router.get("/monthly", response_model=list[MonthlyPoint])
def monthly(f: analytics.Filters = Depends(filters), db: Session = Depends(get_db)):
    return analytics.monthly(db, f)


@router.get("/by-category", response_model=list[CategorySpend])
def by_category(f: analytics.Filters = Depends(filters), db: Session = Depends(get_db)):
    return analytics.by_category(db, f)


@router.get("/balance", response_model=list[BalanceSeries])
def balance(f: analytics.Filters = Depends(filters), db: Session = Depends(get_db)):
    return analytics.balance_history(db, f)
