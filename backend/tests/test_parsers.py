from datetime import date
from decimal import Decimal

import pytest

from app.parsers import REGISTRY, ParseError, detect_parser
from app.parsers.base import decode, parse_money
from tests.conftest import fixture_bytes


def test_detects_chase_checking_with_bom_and_trailing_commas():
    text = decode(fixture_bytes("chase_checking.csv"))
    parser = detect_parser(text)
    assert parser.name == "chase_checking"
    result = parser.parse(text)
    assert result.errors == []
    assert len(result.transactions) == 9


def test_checking_rows_are_oldest_first_and_keep_same_day_order():
    result = REGISTRY["chase_checking"].parse(decode(fixture_bytes("chase_checking.csv")))
    txns = result.transactions
    assert txns[0].posted_date == date(2026, 1, 2)
    assert txns[0].amount == Decimal("2500.00")
    assert txns[0].balance == Decimal("3499.55")
    # The file is newest first; within 02/03 the trip happened before the meal.
    assert [t.description for t in txns[-2:]] == ["UBER TRIP HELP.UBER.COM", "UBER EATS 8005928996 CA"]
    assert txns[-1].balance == Decimal("4176.90")


def test_detects_chase_credit():
    text = decode(fixture_bytes("chase_credit.csv"))
    parser = detect_parser(text)
    assert parser.name == "chase_credit"
    txns = parser.parse(text).transactions
    assert txns[0].description == "Payment Thank You-Mobile"
    assert txns[-1].amount == Decimal("-15.49")
    assert txns[-1].bank_category == "Entertainment"
    assert all(t.balance is None for t in txns)


def test_unknown_format_is_rejected():
    with pytest.raises(ParseError, match="Unrecognised"):
        detect_parser("Date,Payee,Value\n01/01/2026,Shop,-1.00\n")


def test_bad_rows_are_reported_not_fatal():
    text = (
        "Details,Posting Date,Description,Amount,Type,Balance,Check or Slip #\n"
        "DEBIT,13/45/2026,BAD DATE,-1.00,DEBIT_CARD,10.00,\n"
        "DEBIT,01/02/2026,OK,-2.00,DEBIT_CARD,8.00,\n"
    )
    result = REGISTRY["chase_checking"].parse(text)
    assert len(result.transactions) == 1
    assert result.errors == ["Line 2: invalid date '13/45/2026'"]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("-1,234.50", "-1234.50"), ("$12", "12.00"), ("(7.25)", "-7.25"), ("0.1", "0.10")],
)
def test_parse_money(raw, expected):
    assert parse_money(raw) == Decimal(expected)


def test_demo_statements_parse_cleanly():
    from app.scripts.seed_demo import generate

    for filename, kind, text in generate(months=2):
        parser = detect_parser(text)
        assert parser.name == ("chase_checking" if kind == "checking" else "chase_credit"), filename
        result = parser.parse(text)
        assert result.errors == [] and result.transactions
