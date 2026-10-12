"""rename posted_date to posting_date; add use_date

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-12

use_date is the date a transaction is counted under. It starts equal to the
posting date and can be adjusted by the user.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.alter_column(
            "posted_date", new_column_name="posting_date", existing_type=sa.Date(), existing_nullable=False
        )
        batch_op.add_column(sa.Column("use_date", sa.Date(), nullable=True))

    op.execute("UPDATE transactions SET use_date = posting_date")

    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.alter_column("use_date", existing_type=sa.Date(), nullable=False)
        batch_op.create_index("ix_transactions_user_use_date", ["user_id", "use_date"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.drop_index("ix_transactions_user_use_date")
        batch_op.drop_column("use_date")
        batch_op.alter_column(
            "posting_date", new_column_name="posted_date", existing_type=sa.Date(), existing_nullable=False
        )
