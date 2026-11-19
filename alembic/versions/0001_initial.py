"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("user_id", UUID(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)

    op.create_table(
        "pairing_codes",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("user_id", UUID(), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("device_id", UUID(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pairing_codes_code_hash", "pairing_codes", ["code_hash"], unique=True)

    op.create_table(
        "devices",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("user_id", UUID(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("last_state", sa.String(32), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("app_version", sa.String(64), nullable=True),
        sa.Column("fcm_token", sa.String(512), nullable=True),
        sa.Column("paired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_devices_user_id", "devices", ["user_id"])

    op.create_table(
        "reminders",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("user_id", UUID(), nullable=False),
        sa.Column("content", sa.String(500), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recurrence", sa.String(255), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("origin", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reminders_user_id", "reminders", ["user_id"])
    op.create_index("ix_reminders_due_at", "reminders", ["due_at"])
    op.create_index("ix_reminders_user_due", "reminders", ["user_id", "due_at"])
    op.create_index(
        "ix_reminders_active_due",
        "reminders",
        ["due_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "reminder_fires",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("reminder_id", UUID(), nullable=False),
        sa.Column("user_id", UUID(), nullable=False),
        sa.Column(
            "fired_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["reminder_id"], ["reminders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reminder_fires_reminder_id", "reminder_fires", ["reminder_id"])
    op.create_index("ix_reminder_fires_user_id", "reminder_fires", ["user_id"])

    op.create_table(
        "change_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", UUID(), nullable=False),
        sa.Column("aggregate_type", sa.String(32), nullable=False),
        sa.Column("aggregate_id", UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_change_log_user_id", "change_log", ["user_id", "id"])

    op.create_table(
        "apsched_jobs",
        sa.Column("job_id", sa.String(191), nullable=False),
        sa.Column("next_run_time", sa.Float(), nullable=True),
        sa.Column("job_state", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("job_id"),
    )
    op.create_index("ix_apsched_jobs_next_run_time", "apsched_jobs", ["next_run_time"])


def downgrade() -> None:
    op.drop_table("apsched_jobs")
    op.drop_table("change_log")
    op.drop_table("reminder_fires")
    op.drop_table("reminders")
    op.drop_table("devices")
    op.drop_table("pairing_codes")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
