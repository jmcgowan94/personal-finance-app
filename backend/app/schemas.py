from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Input(BaseModel):
    """Base for request bodies. Unknown fields are rejected (422) rather than silently
    ignored, so a frontend/backend mismatch shows an error instead of a no-op save."""

    model_config = ConfigDict(extra="forbid")


AccountType = Literal["checking", "savings", "credit", "other"]
CategoryKind = Literal["expense", "income", "transfer"]
MatchType = Literal["contains", "regex"]


class UserOut(ORM):
    id: int
    email: str | None
    first_name: str | None
    last_name: str | None
    theme: str | None
    default_range: str | None
    default_account_id: int | None


RangePreset = Literal["3m", "6m", "12m", "ytd", "all"]


class UserPatch(Input):
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    # null = follow the device's light/dark setting
    theme: Literal["light", "dark"] | None = None
    # Dashboard time window on launch; null = all time
    default_range: RangePreset | None = None
    # Account the pages start filtered to; null = all accounts
    default_account_id: int | None = None


class AccountIn(Input):
    name: str = Field(min_length=1, max_length=100)
    institution: str = Field(default="", max_length=100)
    account_type: AccountType = "checking"
    last4: str | None = Field(default=None, pattern=r"^\d{4}$")


class AccountOut(ORM):
    id: int
    name: str
    institution: str
    account_type: str
    last4: str | None


class ParserOut(BaseModel):
    name: str
    label: str
    institution: str
    account_type: str


class UploadOut(ORM):
    id: int
    account_id: int
    filename: str
    parser_name: str
    rows_total: int
    rows_imported: int
    rows_duplicate: int
    rows_error: int
    created_at: datetime


class CategoryIn(Input):
    name: str = Field(min_length=1, max_length=100)
    kind: CategoryKind = "expense"


class CategoryPatch(Input):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    kind: CategoryKind | None = None


class CategoryOut(ORM):
    id: int
    name: str
    kind: str


class RuleIn(Input):
    category_id: int
    pattern: str = Field(min_length=1, max_length=255)
    match_type: MatchType = "contains"
    priority: int = 0


class RulePatch(Input):
    category_id: int | None = None
    pattern: str | None = Field(default=None, min_length=1, max_length=255)
    match_type: MatchType | None = None
    priority: int | None = None


class RuleOut(ORM):
    id: int
    category_id: int
    pattern: str
    match_type: str
    priority: int


class ApplyRulesOut(BaseModel):
    updated: int


class TransactionOut(ORM):
    id: int
    account_id: int
    posting_date: date
    use_date: date
    description: str
    amount: Decimal
    txn_type: str | None
    balance: Decimal | None
    check_number: str | None
    bank_category: str | None
    category_id: int | None
    category_locked: bool


class TransactionPage(BaseModel):
    items: list[TransactionOut]
    total: int
    page: int
    page_size: int


class TransactionPatch(Input):
    # Only the fields sent are changed.
    category_id: int | None = None
    # null = reset to the posting date
    use_date: date | None = None


class Summary(BaseModel):
    income: Decimal
    spending: Decimal
    net: Decimal
    transaction_count: int


class MonthlyPoint(BaseModel):
    month: str
    income: Decimal
    spending: Decimal
    net: Decimal
    # Total balance at month end (as counted by use date) across accounts that
    # report one; null if none yet
    end_balance: Decimal | None


class CategorySpend(BaseModel):
    category_id: int | None
    category: str
    spending: Decimal


class BalancePoint(BaseModel):
    date: date
    balance: Decimal


class BalanceSeries(BaseModel):
    account_id: int
    account: str
    points: list[BalancePoint]
