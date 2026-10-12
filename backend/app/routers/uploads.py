from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import Settings, get_settings
from app.db import get_db
from app.models import Account, Upload, User
from app.parsers import ParseError
from app.schemas import UploadOut
from app.services.ingest import import_statement
from app.services.ownership import get_owned
from app.storage import Storage, get_storage

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.get("", response_model=list[UploadOut])
def list_uploads(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(Upload).where(Upload.user_id == user.id).order_by(Upload.created_at.desc(), Upload.id.desc())
    ).all()


@router.post("", response_model=UploadOut, status_code=status.HTTP_201_CREATED)
async def create_upload(
    file: UploadFile = File(...),
    account_id: int = Form(...),
    parser_name: str | None = Form(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
    settings: Settings = Depends(get_settings),
):
    account = get_owned(db, Account, account_id, user.id)
    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File is too large")
    try:
        return import_statement(
            db,
            user_id=user.id,
            account=account,
            filename=file.filename or "statement.csv",
            data=data,
            storage=storage,
            parser_name=parser_name or None,
        )
    except ParseError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from None


@router.delete("/{upload_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_upload(
    upload_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
):
    """Delete an upload and every transaction it imported."""
    upload = get_owned(db, Upload, upload_id, user.id)
    key = upload.storage_key
    db.delete(upload)
    db.commit()
    storage.delete(key)
