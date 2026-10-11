"""001_initial_schema — PostGIS extension and core BountyLoop schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-11 11:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import geoalchemy2

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Enums defined with create_type=False so create_table does not duplicate them
user_role_enum = postgresql.ENUM('donor', 'recipient', 'admin', 'volunteer', name='user_role', create_type=False)
donor_kind_enum = postgresql.ENUM('restaurant', 'grocery', 'farm', 'household', 'other', name='donor_kind', create_type=False)
recipient_org_type_enum = postgresql.ENUM('food_bank', 'shelter', 'community_fridge', 'discount_buyer', name='recipient_org_type', create_type=False)
food_category_enum = postgresql.ENUM(
    'produce_fruit', 'produce_vegetable', 'bread_bakery', 'dairy',
    'grains_staples', 'prepared_cooked', 'meat_fish', 'soup_stew',
    'dessert_bakery_sweet', 'beverage', 'condiment_sauce', 'other_unclassified',
    name='food_category',
    create_type=False
)
freshness_grade_enum = postgresql.ENUM(
    'fresh', 'spoiled', 'grade_0_spoiled', 'grade_1_poor', 'grade_2_good', 'grade_3_fresh',
    name='freshness_grade',
    create_type=False
)
hazard_flag_enum = postgresql.ENUM('none', 'suspected_contamination_or_formalin', name='hazard_flag', create_type=False)
donation_status_enum = postgresql.ENUM(
    'draft', 'open', 'matched', 'in_transit', 'completed', 'cancelled', 'expired',
    name='donation_status',
    create_type=False
)
claim_status_enum = postgresql.ENUM('offered', 'accepted', 'declined', 'picked_up', 'failed', name='claim_status', create_type=False)
review_reason_enum = postgresql.ENUM('low_confidence', 'hazard', 'ambiguous_match', 'other', name='review_reason', create_type=False)
review_status_enum = postgresql.ENUM('pending', 'resolved', name='review_status', create_type=False)


def upgrade() -> None:
    # 1. Enable PostGIS extension
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # 2. Create Enums idempotently
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE user_role AS ENUM ('donor', 'recipient', 'admin', 'volunteer');
        EXCEPTION WHEN duplicate_object THEN null; END $$;

        DO $$ BEGIN
            CREATE TYPE donor_kind AS ENUM ('restaurant', 'grocery', 'farm', 'household', 'other');
        EXCEPTION WHEN duplicate_object THEN null; END $$;

        DO $$ BEGIN
            CREATE TYPE recipient_org_type AS ENUM ('food_bank', 'shelter', 'community_fridge', 'discount_buyer');
        EXCEPTION WHEN duplicate_object THEN null; END $$;

        DO $$ BEGIN
            CREATE TYPE food_category AS ENUM (
                'produce_fruit', 'produce_vegetable', 'bread_bakery', 'dairy',
                'grains_staples', 'prepared_cooked', 'meat_fish', 'soup_stew',
                'dessert_bakery_sweet', 'beverage', 'condiment_sauce', 'other_unclassified'
            );
        EXCEPTION WHEN duplicate_object THEN null; END $$;

        DO $$ BEGIN
            CREATE TYPE freshness_grade AS ENUM (
                'fresh', 'spoiled', 'grade_0_spoiled', 'grade_1_poor', 'grade_2_good', 'grade_3_fresh'
            );
        EXCEPTION WHEN duplicate_object THEN null; END $$;

        DO $$ BEGIN
            CREATE TYPE hazard_flag AS ENUM ('none', 'suspected_contamination_or_formalin');
        EXCEPTION WHEN duplicate_object THEN null; END $$;

        DO $$ BEGIN
            CREATE TYPE donation_status AS ENUM (
                'draft', 'open', 'matched', 'in_transit', 'completed', 'cancelled', 'expired'
            );
        EXCEPTION WHEN duplicate_object THEN null; END $$;

        DO $$ BEGIN
            CREATE TYPE claim_status AS ENUM ('offered', 'accepted', 'declined', 'picked_up', 'failed');
        EXCEPTION WHEN duplicate_object THEN null; END $$;

        DO $$ BEGIN
            CREATE TYPE review_reason AS ENUM ('low_confidence', 'hazard', 'ambiguous_match', 'other');
        EXCEPTION WHEN duplicate_object THEN null; END $$;

        DO $$ BEGIN
            CREATE TYPE review_status AS ENUM ('pending', 'resolved');
        EXCEPTION WHEN duplicate_object THEN null; END $$;
    """)

    # 3. users table
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('firebase_uid', sa.String(length=128), nullable=False),
        sa.Column('role', user_role_enum, nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone_e164', sa.String(length=32), nullable=True),
        sa.Column('org_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_firebase_uid', 'users', ['firebase_uid'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # 4. donors table
    op.create_table(
        'donors',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('kind', donor_kind_enum, nullable=False),
        sa.Column('address', sa.Text(), nullable=False),
        sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326, spatial_index=False, from_text='ST_GeogFromText', name='geography', nullable=False), nullable=False),
        sa.Column('timezone', sa.String(length=64), server_default='UTC', nullable=False),
        sa.Column('avg_surplus_schedule', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index('ix_donors_user_id', 'donors', ['user_id'], unique=True)
    op.create_index('idx_donors_location', 'donors', ['location'], unique=False, postgresql_using='gist')

    # 5. recipients table
    op.create_table(
        'recipients',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('org_type', recipient_org_type_enum, nullable=False),
        sa.Column('address', sa.Text(), nullable=False),
        sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326, spatial_index=False, from_text='ST_GeogFromText', name='geography', nullable=False), nullable=False),
        sa.Column('capacity_kg_per_day', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('accepted_items', postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column('cold_chain', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('operating_hours', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('urgency_weight', sa.Numeric(precision=5, scale=2), server_default='1.0', nullable=False),
        sa.Column('is_accepting', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index('ix_recipients_user_id', 'recipients', ['user_id'], unique=True)
    op.create_index('idx_recipients_location', 'recipients', ['location'], unique=False, postgresql_using='gist')

    # 6. donations table
    op.create_table(
        'donations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('donor_id', sa.UUID(), nullable=False),
        sa.Column('photo_paths', postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column('item', food_category_enum, nullable=False),
        sa.Column('item_confidence', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('freshness', freshness_grade_enum, nullable=False),
        sa.Column('freshness_confidence', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('hazard_flag', hazard_flag_enum, server_default='none', nullable=False),
        sa.Column('est_weight_kg', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', donation_status_enum, server_default='draft', nullable=False),
        sa.Column('needs_review', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('model_versions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['donor_id'], ['donors.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_donations_donor_id', 'donations', ['donor_id'], unique=False)
    op.create_index('ix_donations_expires_at', 'donations', ['expires_at'], unique=False)
    op.create_index('ix_donations_status', 'donations', ['status'], unique=False)
    op.create_index('ix_donations_needs_review', 'donations', ['needs_review'], unique=False)

    # 7. claims table
    op.create_table(
        'claims',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('donation_id', sa.UUID(), nullable=False),
        sa.Column('recipient_id', sa.UUID(), nullable=False),
        sa.Column('status', claim_status_enum, server_default='offered', nullable=False),
        sa.Column('score', sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column('score_breakdown', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('offered_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('picked_up_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('proof_photo_path', sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(['donation_id'], ['donations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recipient_id'], ['recipients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_claims_donation_id', 'claims', ['donation_id'], unique=False)
    op.create_index('ix_claims_recipient_id', 'claims', ['recipient_id'], unique=False)
    op.create_index('ix_claims_status', 'claims', ['status'], unique=False)

    # 8. impact_log table
    op.create_table(
        'impact_log',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('donation_id', sa.UUID(), nullable=False),
        sa.Column('kg_rescued', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('meals_equivalent', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('co2e_avoided_kg', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('computed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('method_version', sa.String(length=32), server_default='v1.0', nullable=False),
        sa.ForeignKeyConstraint(['donation_id'], ['donations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('donation_id')
    )
    op.create_index('ix_impact_log_donation_id', 'impact_log', ['donation_id'], unique=True)

    # 9. agent_events table
    op.create_table(
        'agent_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('donation_id', sa.UUID(), nullable=True),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('model', sa.String(length=64), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['donation_id'], ['donations.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_agent_events_donation_id', 'agent_events', ['donation_id'], unique=False)
    op.create_index('ix_agent_events_event_type', 'agent_events', ['event_type'], unique=False)

    # 10. review_queue table
    op.create_table(
        'review_queue',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('donation_id', sa.UUID(), nullable=False),
        sa.Column('reason', review_reason_enum, nullable=False),
        sa.Column('status', review_status_enum, server_default='pending', nullable=False),
        sa.Column('resolved_by', sa.UUID(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['donation_id'], ['donations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_review_queue_donation_id', 'review_queue', ['donation_id'], unique=False)
    op.create_index('ix_review_queue_status', 'review_queue', ['status'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order of foreign key dependencies
    op.drop_table('review_queue')
    op.drop_table('agent_events')
    op.drop_table('impact_log')
    op.drop_table('claims')
    op.drop_table('donations')
    op.drop_table('recipients')
    op.drop_table('donors')
    op.drop_table('users')

    # Drop enums safely
    op.execute("""
        DROP TYPE IF EXISTS review_status;
        DROP TYPE IF EXISTS review_reason;
        DROP TYPE IF EXISTS claim_status;
        DROP TYPE IF EXISTS donation_status;
        DROP TYPE IF EXISTS hazard_flag;
        DROP TYPE IF EXISTS freshness_grade;
        DROP TYPE IF EXISTS food_category;
        DROP TYPE IF EXISTS recipient_org_type;
        DROP TYPE IF EXISTS donor_kind;
        DROP TYPE IF EXISTS user_role;
    """)
