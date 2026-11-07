"""004_donor_surplus_forecasts — Add donor_surplus_forecasts table for Phase 11.

Revision ID: 004_donor_surplus_forecasts
Revises: 003_sms_messages
Create Date: 2026-11-07 21:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "004_donor_surplus_forecasts"
down_revision: Union[str, None] = "003_sms_messages"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "donor_surplus_forecasts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("donor_id", sa.UUID(), nullable=False),
        sa.Column("forecast_date", sa.Date(), nullable=False),
        sa.Column("predicted_kg", sa.Float(), nullable=False),
        sa.Column("confidence_lower_kg", sa.Float(), nullable=True),
        sa.Column("confidence_upper_kg", sa.Float(), nullable=True),
        sa.Column("model_version", sa.String(length=50), server_default="sarimax_v1", nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["donor_id"], ["donors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("donor_id", "forecast_date", "model_version", name="uq_donor_forecast_date_model"),
    )
    op.create_index(
        "ix_donor_surplus_forecasts_donor_id",
        "donor_surplus_forecasts",
        ["donor_id"],
        unique=False,
    )
    op.create_index(
        "ix_donor_surplus_forecasts_forecast_date",
        "donor_surplus_forecasts",
        ["forecast_date"],
        unique=False,
    )
    op.create_index(
        "ix_donor_surplus_forecasts_model_version",
        "donor_surplus_forecasts",
        ["model_version"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_donor_surplus_forecasts_model_version", table_name="donor_surplus_forecasts")
    op.drop_index("ix_donor_surplus_forecasts_forecast_date", table_name="donor_surplus_forecasts")
    op.drop_index("ix_donor_surplus_forecasts_donor_id", table_name="donor_surplus_forecasts")
    op.drop_table("donor_surplus_forecasts")

