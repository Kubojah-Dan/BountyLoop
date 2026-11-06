"""003_sms_messages — Add sms_messages table for Twilio SMS audit and daily cap tracking

Revision ID: 003_sms_messages
Revises: 002_devices_table
Create Date: 2026-11-06 23:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "003_sms_messages"
down_revision: Union[str, None] = "002_devices_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sms_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("direction", sa.String(length=16), server_default="outbound", nullable=False),
        sa.Column("to_phone", sa.String(length=32), nullable=False),
        sa.Column("from_phone", sa.String(length=32), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="sent", nullable=False),
        sa.Column("sid", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("claim_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sms_messages_to_phone", "sms_messages", ["to_phone"], unique=False)
    op.create_index("ix_sms_messages_status", "sms_messages", ["status"], unique=False)
    op.create_index("ix_sms_messages_sid", "sms_messages", ["sid"], unique=False)
    op.create_index("ix_sms_messages_user_id", "sms_messages", ["user_id"], unique=False)
    op.create_index("ix_sms_messages_claim_id", "sms_messages", ["claim_id"], unique=False)
    op.create_index("ix_sms_messages_created_at", "sms_messages", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_sms_messages_created_at", table_name="sms_messages")
    op.drop_index("ix_sms_messages_claim_id", table_name="sms_messages")
    op.drop_index("ix_sms_messages_user_id", table_name="sms_messages")
    op.drop_index("ix_sms_messages_sid", table_name="sms_messages")
    op.drop_index("ix_sms_messages_status", table_name="sms_messages")
    op.drop_index("ix_sms_messages_to_phone", table_name="sms_messages")
    op.drop_table("sms_messages")

