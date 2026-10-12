from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import Account, User
from app.parsers import REGISTRY
from app.schemas import AccountIn, AccountOut, ParserOut

router = APIRouter(tags=["accounts"])


@router.get("/accounts", response_model=list[AccountOut])
def list_accounts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(select(Account).where(Account.user_id == user.id).order_by(Account.name)).all()


@router.post("/accounts", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(
    body: AccountIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    exists = db.scalar(select(Account).where(Account.user_id == user.id, Account.name == body.name))
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with that name already exists")
    account = Account(user_id=user.id, **body.model_dump())
    db.add(account)
    db.commit()
    return account


@router.get("/parsers", response_model=list[ParserOut])
def list_parsers():
    return [
        ParserOut(name=p.name, label=p.label, institution=p.institution, account_type=p.account_type)
        for p in REGISTRY.values()
    ]
