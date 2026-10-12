"""Import a statement file: parse, de-duplicate, categorise, save."""

import hashlib
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Account, Transaction, Upload
from app.parsers import REGISTRY, ParseError, detect_parser
from app.parsers.base import ParsedTransaction, decode
from app.services.categorize import load_rules
from app.storage import Storage


def dedupe_hash(account_id: int, txn: ParsedTransaction, occurrence: int) -> str:
    """Identity of a transaction, stable across re-uploads of overlapping statements.

    ``occurrence`` distinguishes genuinely identical rows on the same day (e.g. two
    identical coffees), which are numbered in file order.
    """
    parts = [
        str(account_id),
        txn.posting_date.isoformat(),
        str(txn.amount),
        txn.description,
        "" if txn.balance is None else str(txn.balance),
        str(occurrence),
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def import_statement(
    db: Session,
    *,
    user_id: int,
    account: Account,
    filename: str,
    data: bytes,
    storage: Storage,
    parser_name: str | None = None,
) -> Upload:
    if account.user_id != user_id:
        raise PermissionError("Account does not belong to user")

    text = decode(data)
    if parser_name:
        if parser_name not in REGISTRY:
            raise ParseError(f"Unknown format {parser_name!r}")
        parser = REGISTRY[parser_name]
    else:
        parser = detect_parser(text)
    result = parser.parse(text)
    if not result.transactions:
        detail = "; ".join(result.errors[:5]) or "the file contains no transactions"
        raise ParseError(f"No transactions could be read: {detail}")

    seen: Counter[tuple] = Counter()
    hashed: list[tuple[str, ParsedTransaction]] = []
    for txn in result.transactions:
        key = (txn.posting_date, txn.amount, txn.description, txn.balance)
        hashed.append((dedupe_hash(account.id, txn, seen[key]), txn))
        seen[key] += 1

    existing = set(
        db.scalars(
            select(Transaction.dedupe_hash).where(
                Transaction.user_id == user_id,
                Transaction.dedupe_hash.in_([h for h, _ in hashed]),
            )
        )
    )

    upload = Upload(
        user_id=user_id,
        account_id=account.id,
        filename=filename[:255],
        storage_key=storage.save(user_id, data),
        parser_name=parser.name,
        rows_total=len(result.transactions) + len(result.errors),
        rows_error=len(result.errors),
    )
    db.add(upload)
    db.flush()

    rules = load_rules(db, user_id)
    imported = 0
    for sequence, (digest, txn) in enumerate(hashed):
        if digest in existing:
            continue
        db.add(
            Transaction(
                user_id=user_id,
                account_id=account.id,
                upload_id=upload.id,
                posting_date=txn.posting_date,
                use_date=txn.posting_date,
                sequence=sequence,
                description=txn.description[:500],
                amount=txn.amount,
                txn_type=txn.txn_type,
                balance=txn.balance,
                check_number=txn.check_number,
                bank_category=txn.bank_category,
                category_id=rules.match(txn.description),
                dedupe_hash=digest,
            )
        )
        imported += 1

    upload.rows_imported = imported
    upload.rows_duplicate = len(hashed) - imported
    db.commit()
    return upload
