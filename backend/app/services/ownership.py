from typing import TypeVar

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

T = TypeVar("T")


def get_owned(db: Session, model: type[T], obj_id: int, user_id: int) -> T:
    """Fetch a row by id, but only if it belongs to ``user_id``; otherwise 404."""
    obj = db.scalar(select(model).where(model.id == obj_id, model.user_id == user_id))
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{model.__name__} not found")
    return obj
