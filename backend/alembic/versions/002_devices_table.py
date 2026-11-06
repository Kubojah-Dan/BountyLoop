"""002_devices_table — Add devices table for FCM push notifications

Revision ID: 002_devices_table
Revises: 001_initial_schema
Create Date: 2026-11-06 18:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002_devices_table"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "devices",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("fcm_token", sa.String(length=512), nullable=False),
        sa.Column("platform", sa.String(length=32), server_default="android", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fcm_token"),
    )
    op.create_index("ix_devices_user_id", "devices", ["user_id"], unique=False)
    op.create_index("ix_devices_fcm_token", "devices", ["fcm_token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_devices_fcm_token", table_name="devices")
    op.drop_index("ix_devices_user_id", table_name="devices")
    op.drop_table("devices")
