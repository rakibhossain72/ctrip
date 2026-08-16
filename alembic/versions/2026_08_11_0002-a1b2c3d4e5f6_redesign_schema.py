"""redesign schema to unified architecture

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-08-11 02:00:00.000000

This is a baseline reset per "new Architecture.txt" Phase 7:

New tables:     users, chains, payment_events, payment_state_changes
Redesigned:     payments, api_keys, webhook_attempts
Dropped:        admin_users, transactions, payment_wallets

Legacy tables are dropped first (the previous migrations were removed from
the tree), then the full redesigned schema is created.
"""
import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = None
branch_labels = None
depends_on = None


def _dialect():
    return op.get_bind().dialect.name


def _json():
    """JSONB on PostgreSQL, plain JSON elsewhere (SQLite-compatible)."""
    if _dialect() == "postgresql":
        from sqlalchemy.dialects.postgresql import JSONB  # pylint: disable=import-outside-toplevel

        return JSONB()
    return sa.JSON()


def _now_default():
    if _dialect() == "postgresql":
        return text("now()")
    return text("(CURRENT_TIMESTAMP)")


def _drop_if_exists(tables: list[str]) -> None:
    """Drop legacy tables in child->parent FK order (no CASCADE for SQLite)."""
    for table in tables:
        op.execute(text(f"DROP TABLE IF EXISTS {table}"))


def upgrade() -> None:
    """Apply the schema redesign: drop legacy tables and create new ones."""
    _drop_if_exists(
        [
            "transactions",
            "payment_wallets",
            "webhook_attempts",
            "payments",
            "api_keys",
            "admin_users",
        ]
    )

    # --- users ---------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=True),
        sa.Column(
            "role", sa.String(length=50), nullable=False, server_default="admin"
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=text("true")
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=_now_default()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=_now_default()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )

    # --- chains ---------------------------------------------------------------
    op.create_table(
        "chains",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=True),
        sa.Column(
            "is_enabled", sa.Boolean(), nullable=False, server_default=text("true")
        ),
        sa.Column("rpc_url", sa.String(length=500), nullable=False),
        sa.Column("ws_url", sa.String(length=500), nullable=True),
        sa.Column(
            "poa", sa.Boolean(), nullable=False, server_default=text("false")
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=_now_default()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=_now_default()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_chains_name"),
    )

    # --- api_keys -------------------------------------------------------------
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("key_prefix", sa.String(length=12), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=text("true")
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=_now_default()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=_now_default()),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash", name="uq_api_keys_key_hash"),
    )
    op.create_index("ix_api_keys_key_prefix", "api_keys", ["key_prefix"])
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])

    # --- payments -------------------------------------------------------------
    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("api_key_id", sa.Uuid(), nullable=False),
        sa.Column("chain_id", sa.Integer(), nullable=False),
        sa.Column("address", sa.String(length=42), nullable=False),
        sa.Column("amount_raw", sa.BigInteger(), nullable=False),
        sa.Column("token_contract", sa.String(length=42), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("confirmations", sa.Integer(), nullable=False, server_default=text("0")),
        sa.Column("detected_at", sa.DateTime(), nullable=True),
        sa.Column("detected_in_block", sa.BigInteger(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("settled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=_now_default()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=_now_default()),
        sa.ForeignKeyConstraint(["api_key_id"], ["api_keys.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["chain_id"], ["chains.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint("amount_raw > 0", name="chk_payment_amount_positive"),
        sa.CheckConstraint("length(address) = 42", name="chk_payment_address_length"),
        sa.CheckConstraint(
            "status IN ('pending', 'detected', 'confirmed', 'paid', "
            "'expired', 'settled', 'failed')",
            name="chk_payment_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_payments_chain_status_expires",
        "payments",
        ["chain_id", "status", "expires_at"],
    )
    op.create_index(
        "ix_payments_user_created", "payments", ["user_id", text("created_at DESC")]
    )
    op.create_index(
        "ix_payments_api_key_created",
        "payments",
        ["api_key_id", text("created_at DESC")],
    )
    op.create_index(
        "ix_payments_status_created", "payments", ["status", "created_at"]
    )
    op.create_index("ix_payments_address", "payments", ["address"])

    # --- payment_events -------------------------------------------------------
    op.create_table(
        "payment_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("payment_id", sa.Uuid(), nullable=False),
        sa.Column("chain_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=20), nullable=False),
        sa.Column("tx_hash", sa.String(length=66), nullable=False),
        sa.Column("log_index", sa.Integer(), nullable=True),
        sa.Column("token_contract", sa.String(length=42), nullable=True),
        sa.Column("value_raw", sa.BigInteger(), nullable=False),
        sa.Column("from_address", sa.String(length=42), nullable=False),
        sa.Column("to_address", sa.String(length=42), nullable=False),
        sa.Column("block_number", sa.BigInteger(), nullable=False),
        sa.Column("confirmations", sa.Integer(), nullable=False, server_default=text("0")),
        sa.Column("recorded_at", sa.DateTime(), nullable=False, server_default=_now_default()),
        sa.ForeignKeyConstraint(["chain_id"], ["chains.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="CASCADE"),
        sa.CheckConstraint("event_type IN ('native', 'erc20')", name="chk_event_type"),
        sa.CheckConstraint("value_raw > 0", name="chk_event_value_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tx_hash", "log_index", name="ux_payment_events_tx_log"),
    )
    op.create_index(
        "ix_payment_events_payment_recorded",
        "payment_events",
        ["payment_id", text("recorded_at DESC")],
    )
    op.create_index(
        "ix_payment_events_chain_block", "payment_events", ["chain_id", "block_number"]
    )
    op.create_index(
        "ix_payment_events_to_address",
        "payment_events",
        ["to_address", text("recorded_at DESC")],
    )

    # --- payment_state_changes -------------------------------------------------
    op.create_table(
        "payment_state_changes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("payment_id", sa.Uuid(), nullable=False),
        sa.Column("from_status", sa.String(length=20), nullable=False),
        sa.Column("to_status", sa.String(length=20), nullable=False),
        sa.Column("changed_at", sa.DateTime(), nullable=False, server_default=_now_default()),
        sa.Column("metadata", _json(), nullable=True),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_state_changes_payment_time",
        "payment_state_changes",
        ["payment_id", text("changed_at DESC")],
    )
    op.create_index("ix_state_changes_time", "payment_state_changes", ["changed_at"])

    # --- webhook_attempts ------------------------------------------------------
    op.create_table(
        "webhook_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("payment_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("webhook_url", sa.String(length=500), nullable=False),
        sa.Column("payload", _json(), nullable=False),
        sa.Column("webhook_secret", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default=text("0")),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=_now_default()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=_now_default()),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "status IN ('pending', 'success', 'failed')", name="chk_webhook_status"
        ),
        sa.CheckConstraint(
            "retry_count >= 0 AND retry_count <= 10", name="chk_webhook_retry_count"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_webhooks_status_retry", "webhook_attempts", ["status", "next_retry_at"]
    )
    op.create_index("ix_webhooks_payment", "webhook_attempts", ["payment_id"])
    op.create_index(
        "ix_webhooks_created", "webhook_attempts", [text("created_at DESC")]
    )


def downgrade() -> None:
    """Drop the redesigned schema to revert to the legacy layout."""
    _drop_if_exists(
        [
            "payment_events",
            "payment_state_changes",
            "webhook_attempts",
            "payments",
            "api_keys",
            "chains",
            "users",
        ]
    )
