from app.parsers.base import (
    ParsedTransaction,
    StatementParser,
    blank_to_none,
    parse_money,
    parse_optional_money,
    parse_us_date,
    register,
)


@register
class ChaseCheckingParser(StatementParser):
    name = "chase_checking"
    label = "Chase checking/savings"
    institution = "Chase"
    account_type = "checking"
    required_headers = frozenset({"Details", "Posting Date", "Description", "Amount", "Balance"})

    def parse_row(self, row: dict[str, str]) -> ParsedTransaction:
        if not row["Description"]:
            raise ValueError("missing description")
        return ParsedTransaction(
            posted_date=parse_us_date(row["Posting Date"]),
            description=row["Description"],
            amount=parse_money(row["Amount"]),
            txn_type=blank_to_none(row.get("Type", "")),
            balance=parse_optional_money(row["Balance"]),
            check_number=blank_to_none(row.get("Check or Slip #", "")),
        )


@register
class ChaseCreditParser(StatementParser):
    name = "chase_credit"
    label = "Chase credit card"
    institution = "Chase"
    account_type = "credit"
    required_headers = frozenset({"Transaction Date", "Post Date", "Description", "Amount"})

    def parse_row(self, row: dict[str, str]) -> ParsedTransaction:
        if not row["Description"]:
            raise ValueError("missing description")
        return ParsedTransaction(
            posted_date=parse_us_date(row["Post Date"]),
            description=row["Description"],
            amount=parse_money(row["Amount"]),
            txn_type=blank_to_none(row.get("Type", "")),
            bank_category=blank_to_none(row.get("Category", "")),
        )
