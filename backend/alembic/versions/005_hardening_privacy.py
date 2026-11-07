"""005_hardening_privacy — Add consent_model_training to users and idempotency_key to donations.

Revision ID: 005_hardening_privacy
Revises: 004_donor_surplus_forecasts
Create Date: 2026-11-07 22:35:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "005_hardening_privacy"
down_revision: Union[str, None] = "004_donor_surplus_forecasts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Privacy consent toggle on users table
    op.add_column(
        "users",
        sa.Column(
            "consent_model_training",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )

    # 2. Idempotency key for offline outbox sync on donations table
    op.add_column(
        "donations",
        sa.Column(
            "idempotency_key",
            sa.String(length=64),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_donations_idempotency_key",
        "donations",
        ["idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_donations_idempotency_key", table_name="donations")
    op.drop_column("donations", "idempotency_key")
    op.drop_column("users", "consent_model_training")

