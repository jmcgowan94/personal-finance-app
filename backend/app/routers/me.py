from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import User
from app.schemas import UserOut, UserPatch

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=UserOut)
def get_me(user: User = Depends(get_current_user)):
    return user


@router.patch("", response_model=UserOut)
def update_me(body: UserPatch, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update the signed-in user's profile and preferences. Blank names are stored as null."""
    changes = body.model_dump(exclude_unset=True)
    for key in ("first_name", "last_name"):
        if key in changes:
            setattr(user, key, (changes[key] or "").strip() or None)
    if "theme" in changes:
        user.theme = changes["theme"]
    db.commit()
    return user
