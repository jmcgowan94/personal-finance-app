"""Resolves the user behind each request.

This is the single seam between the app and its identity provider. Routers depend
on ``get_current_user`` and never look at headers or tokens themselves.
"""

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models import User
from app.services.categorize import seed_default_categories


def get_or_create_user(db: Session, subject: str, email: str | None = None) -> User:
    user = db.scalar(select(User).where(User.auth_subject == subject))
    if user is None:
        try:
            user = User(auth_subject=subject, email=email)
            db.add(user)
            db.flush()
            seed_default_categories(db, user.id)
            db.commit()
        except IntegrityError:
            # Another request created this user at the same moment.
            db.rollback()
            user = db.scalar(select(User).where(User.auth_subject == subject))
    return user


def _subject_from_cognito_token(request: Request, settings: Settings) -> tuple[str, str | None]:
    """Validate a Cognito access/ID token and return (sub, email).

    Implement when moving to AWS: read the ``Authorization: Bearer`` header, verify
    the JWT signature against the user pool's JWKS
    (https://cognito-idp.{region}.amazonaws.com/{pool_id}/.well-known/jwks.json),
    check ``iss``, ``exp`` and ``client_id``/``aud``, then return the ``sub`` claim.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Cognito authentication is not configured yet",
    )


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    if settings.auth_mode == "local":
        return get_or_create_user(db, settings.local_user_subject)
    subject, email = _subject_from_cognito_token(request, settings)
    return get_or_create_user(db, subject, email)
