"""Database models.

Every user-owned table carries a non-null, indexed ``user_id``. Queries must always
filter on it - that is what keeps one user's data invisible to another.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

Money = Numeric(12, 2)


class Base(DeclarativeBase):
    # Named constraints keep future Alembic migrations working on SQLite and Postgres.
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Stable identity from the auth provider ("local" locally, Cognito "sub" on AWS).
    auth_subject: Mapped[str] = mapped_column(String(255), unique=True)
    email: Mapped[str | None] = mapped_column(String(320))
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    # "light" | "dark"; null means follow the device's setting.
    theme: Mapped[str | None] = mapped_column(String(10))
    # Dashboard time window on launch: "3m" | "6m" | "12m" | "ytd" | "all"; null means "all".
    default_range: Mapped[str | None] = mapped_column(String(10))
    # Account the Dashboard and Transactions start filtered to; null means all accounts.
    # use_alter: users and accounts reference each other.
    default_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL", use_alter=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class UserOwned:
    """Mixin for tables whose rows belong to exactly one user."""

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )


class Account(UserOwned, Base):
    __tablename__ = "accounts"
    __table_args__ = (UniqueConstraint("user_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    institution: Mapped[str] = mapped_column(String(100), default="")
    account_type: Mapped[str] = mapped_column(String(20), default="checking")
    last4: Mapped[str | None] = mapped_column(String(4))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Upload(UserOwned, Base):
    __tablename__ = "uploads"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(512))
    parser_name: Mapped[str] = mapped_column(String(50))
    rows_total: Mapped[int] = mapped_column(Integer, default=0)
    rows_imported: Mapped[int] = mapped_column(Integer, default=0)
    rows_duplicate: Mapped[int] = mapped_column(Integer, default=0)
    rows_error: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    account: Mapped[Account] = relationship()


class Category(UserOwned, Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("user_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    # "expense" | "income" | "transfer". Transfers are excluded from income/spend totals.
    kind: Mapped[str] = mapped_column(String(20), default="expense")


class CategoryRule(UserOwned, Base):
    __tablename__ = "category_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), index=True
    )
    pattern: Mapped[str] = mapped_column(String(255))
    # "contains" (case-insensitive substring) | "regex" (case-insensitive)
    match_type: Mapped[str] = mapped_column(String(20), default="contains")
    priority: Mapped[int] = mapped_column(Integer, default=0)


class Transaction(UserOwned, Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("user_id", "dedupe_hash"),
        Index("ix_transactions_user_date", "user_id", "posted_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    upload_id: Mapped[int] = mapped_column(
        ForeignKey("uploads.id", ondelete="CASCADE"), index=True
    )
    posted_date: Mapped[date] = mapped_column(Date)
    # Chronological position within its upload; orders same-day rows.
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str] = mapped_column(String(500))
    # Negative = money out, positive = money in.
    amount: Mapped[Decimal] = mapped_column(Money)
    txn_type: Mapped[str | None] = mapped_column(String(50))
    balance: Mapped[Decimal | None] = mapped_column(Money)
    check_number: Mapped[str | None] = mapped_column(String(50))
    bank_category: Mapped[str | None] = mapped_column(String(100))
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )
    # True once the user sets a category by hand; rules then leave it alone.
    category_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    dedupe_hash: Mapped[str] = mapped_column(String(64))

    category: Mapped[Category | None] = relationship()
    account: Mapped[Account] = relationship()
