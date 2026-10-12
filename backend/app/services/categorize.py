"""Rule-based transaction categorisation."""

import re
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category, CategoryRule, Transaction

# (name, kind, keyword patterns). Seeded for every new user; all editable.
DEFAULT_CATEGORIES: list[tuple[str, str, list[str]]] = [
    ("Income", "income", ["PAYROLL", "DIRECT DEP", "SALARY", "INTEREST PAYMENT"]),
    ("Housing", "expense", ["RENT", "MORTGAGE", "HOA"]),
    ("Groceries", "expense", ["WHOLEFDS", "WHOLE FOODS", "TRADER JOE", "SAFEWAY", "KROGER", "COSTCO", "ALDI"]),
    ("Dining", "expense", ["UBER EATS", "DOORDASH", "GRUBHUB", "STARBUCKS", "CHIPOTLE", "RESTAURANT", "CAFE"]),
    ("Transport", "expense", ["UBER", "LYFT", "SHELL", "CHEVRON", "EXXON", "PARKING", "METRO"]),
    ("Shopping", "expense", ["AMAZON", "AMZN", "TARGET", "WALMART", "BEST BUY"]),
    ("Utilities", "expense", ["COMCAST", "XFINITY", "VERIZON", "AT&T", "T-MOBILE", "ELECTRIC", "WATER", "PG&E"]),
    ("Subscriptions", "expense", ["NETFLIX", "SPOTIFY", "HULU", "APPLE.COM/BILL", "YOUTUBE"]),
    ("Health", "expense", ["CVS", "WALGREENS", "PHARMACY", "DENTAL", "MEDICAL"]),
    ("Fees", "expense", ["FEE", "INTEREST CHARGE"]),
    ("Transfers", "transfer", ["TRANSFER", "ZELLE", "VENMO", "PAYMENT THANK YOU", "AUTOPAY", "CREDIT CRD", "CARD SERV"]),
]


def seed_default_categories(db: Session, user_id: int) -> None:
    for name, kind, patterns in DEFAULT_CATEGORIES:
        category = Category(user_id=user_id, name=name, kind=kind)
        db.add(category)
        db.flush()
        db.add_all(
            CategoryRule(user_id=user_id, category_id=category.id, pattern=p, match_type="contains")
            for p in patterns
        )


def validate_pattern(pattern: str, match_type: str) -> None:
    if not pattern.strip():
        raise ValueError("Pattern must not be empty")
    if match_type == "regex":
        try:
            re.compile(pattern)
        except re.error as exc:
            raise ValueError(f"Invalid regular expression: {exc}") from None
    elif match_type != "contains":
        raise ValueError("match_type must be 'contains' or 'regex'")


@dataclass
class CompiledRule:
    category_id: int
    matches: Callable[[str], bool]


class RuleSet:
    """A user's rules, ordered so the most specific rule wins.

    Higher ``priority`` first; ties go to the longer pattern, so "UBER EATS"
    (Dining) beats "UBER" (Transport) without any manual priority.
    """

    def __init__(self, rules: list[CategoryRule]):
        ordered = sorted(rules, key=lambda r: (-r.priority, -len(r.pattern), r.id))
        self.rules = [self._compile(r) for r in ordered]

    @staticmethod
    def _compile(rule: CategoryRule) -> CompiledRule:
        if rule.match_type == "regex":
            regex = re.compile(rule.pattern, re.IGNORECASE)
            return CompiledRule(rule.category_id, lambda text: regex.search(text) is not None)
        needle = rule.pattern.casefold()
        return CompiledRule(rule.category_id, lambda text: needle in text.casefold())

    def match(self, description: str) -> int | None:
        for rule in self.rules:
            if rule.matches(description):
                return rule.category_id
        return None


def load_rules(db: Session, user_id: int) -> RuleSet:
    return RuleSet(list(db.scalars(select(CategoryRule).where(CategoryRule.user_id == user_id))))


def apply_rules(db: Session, user_id: int) -> int:
    """Re-categorise every transaction the user hasn't categorised by hand.

    Returns the number of transactions whose category changed.
    """
    rules = load_rules(db, user_id)
    changed = 0
    txns = db.scalars(
        select(Transaction).where(
            Transaction.user_id == user_id, Transaction.category_locked.is_(False)
        )
    )
    for txn in txns:
        category_id = rules.match(txn.description)
        if category_id != txn.category_id:
            txn.category_id = category_id
            changed += 1
    db.commit()
    return changed
