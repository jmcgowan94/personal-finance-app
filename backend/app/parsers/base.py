"""Statement parser framework.

A parser turns the text of one bank's CSV export into ``ParsedTransaction`` rows.
To support a new bank, subclass ``StatementParser``, implement ``parse_row`` and
decorate the class with ``@register``.
"""

import csv
import io
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import ClassVar


class ParseError(Exception):
    """The file as a whole could not be parsed."""


@dataclass
class ParsedTransaction:
    posting_date: date
    description: str
    amount: Decimal  # negative = money out
    txn_type: str | None = None
    balance: Decimal | None = None
    check_number: str | None = None
    bank_category: str | None = None


@dataclass
class ParseResult:
    # In chronological order (oldest first).
    transactions: list[ParsedTransaction] = field(default_factory=list)
    # Human-readable messages for rows that were skipped.
    errors: list[str] = field(default_factory=list)


class StatementParser(ABC):
    name: ClassVar[str]
    label: ClassVar[str]
    institution: ClassVar[str]
    account_type: ClassVar[str]
    required_headers: ClassVar[frozenset[str]]

    def detect(self, headers: list[str]) -> bool:
        return self.required_headers <= {h.strip() for h in headers}

    @abstractmethod
    def parse_row(self, row: dict[str, str]) -> ParsedTransaction:
        """Parse one CSV row; raise ValueError if the row is invalid."""

    def parse(self, text: str) -> ParseResult:
        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames is None or not self.detect(reader.fieldnames):
            raise ParseError(f"File does not look like a {self.label} export")
        reader.fieldnames = [h.strip() for h in reader.fieldnames]

        result = ParseResult()
        for line_no, row in enumerate(reader, start=2):
            # Extra trailing columns land under the None key; ignore them.
            row = {k: (v or "").strip() for k, v in row.items() if k is not None}
            if not any(row.values()):
                continue
            try:
                result.transactions.append(self.parse_row(row))
            except (ValueError, KeyError) as exc:
                result.errors.append(f"Line {line_no}: {exc}")

        txns = result.transactions
        # Banks often export newest first; normalise to oldest first while keeping
        # the relative order of same-day rows (needed for running balances).
        if len(txns) > 1 and txns[0].posting_date > txns[-1].posting_date:
            txns.reverse()
        txns.sort(key=lambda t: t.posting_date)
        return result


REGISTRY: dict[str, StatementParser] = {}


def register(cls: type[StatementParser]) -> type[StatementParser]:
    REGISTRY[cls.name] = cls()
    return cls


def decode(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252")


def read_headers(text: str) -> list[str]:
    first_line = text.splitlines()[0] if text.strip() else ""
    return next(csv.reader([first_line]), [])


def detect_parser(text: str) -> StatementParser:
    headers = read_headers(text)
    for parser in REGISTRY.values():
        if parser.detect(headers):
            return parser
    raise ParseError(
        "Unrecognised CSV format. Supported formats: "
        + ", ".join(p.label for p in REGISTRY.values())
    )


def parse_us_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%m/%d/%Y").date()
    except ValueError:
        raise ValueError(f"invalid date {value!r}") from None


def parse_money(value: str) -> Decimal:
    cleaned = value.replace("$", "").replace(",", "").strip()
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    if negative:
        cleaned = cleaned[1:-1]
    try:
        amount = Decimal(cleaned)
    except InvalidOperation:
        raise ValueError(f"invalid amount {value!r}") from None
    return (-amount if negative else amount).quantize(Decimal("0.01"))


def parse_optional_money(value: str) -> Decimal | None:
    return parse_money(value) if value.strip() else None


def blank_to_none(value: str) -> str | None:
    return value or None
