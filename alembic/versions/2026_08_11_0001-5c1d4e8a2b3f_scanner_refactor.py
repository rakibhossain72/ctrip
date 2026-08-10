"""scanner refactor: payments.chain_id, transactions dedup columns, drop chain_states

Revision ID: 5c1d4e8a2b3f
Revises: 4f3532210224
Create Date: 2026-08-11 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.blockchain.chains import chain_by_name


# revision identifiers, used by Alembic.
revision: str = "5c1d4e8a2b3f"
down_revision: Union[str, Sequence[str], None] = "4f3532210224"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_tx_hash_unique_sqlite(bind) -> None:
    """Rebuild the SQLite transactions table without the legacy tx_hash UNIQUE."""
    meta = sa.MetaData()
    transactions = sa.Table("transactions", meta, autoload_with=bind)
    for cons in list(transactions.constraints):
        if isinstance(cons, sa.UniqueConstraint) and list(cons.columns) == [
            transactions.c.tx_hash
        ]:
            transactions.constraints.remove(cons)
    with op.batch_alter_table(
        "transactions", copy_from=transactions, recreate="always"
    ) as batch_op:
        batch_op.add_column(sa.Column("log_index", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("dedup_key", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("token_contract_address", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("value_raw", sa.BigInteger(), nullable=True))


def _drop_tx_hash_unique_postgres(bind) -> None:
    """Drop the legacy unique constraint on transactions.tx_hash (PostgreSQL)."""
    inspector = sa.inspect(bind)
    for cons in inspector.get_unique_constraints("transactions"):
        if cons["column_names"] == ["tx_hash"] and cons.get("name"):
            op.drop_constraint(cons["name"], "transactions", type_="unique")
            break
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.add_column(sa.Column("log_index", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("dedup_key", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("token_contract_address", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("value_raw", sa.BigInteger(), nullable=True))


def upgrade() -> None:
    """Upgrade database schema.

    Apply changes to move database schema forward.
    """
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    # 1. Add payments.chain_id (nullable, backfilled below)
    with op.batch_alter_table("payments") as batch_op:
        batch_op.add_column(sa.Column("chain_id", sa.Integer(), nullable=True))

    # 2. Backfill payments.chain_id from the chain name via the config loader
    rows = bind.execute(
        sa.text("SELECT id, chain FROM payments WHERE chain_id IS NULL")
    ).fetchall()
    for payment_id, chain_name in rows:
        cfg = chain_by_name(chain_name)
        if cfg is not None:
            bind.execute(
                sa.text("UPDATE payments SET chain_id = :chain_id WHERE id = :id"),
                {"chain_id": cfg.chain_id, "id": payment_id},
            )

    with op.batch_alter_table("payments") as batch_op:
        batch_op.create_index("ix_payments_chain_id", ["chain_id"])

    # 3. transactions: replace the single unique tx_hash with dedup_key + composite
    if is_sqlite:
        _drop_tx_hash_unique_sqlite(bind)
    else:
        _drop_tx_hash_unique_postgres(bind)

    # Backfill dedup_key for pre-existing rows using the native-style key.
    bind.execute(
        sa.text(
            "UPDATE transactions SET dedup_key = tx_hash || char(58) || '0' "
            "WHERE dedup_key IS NULL"
        )
    )

    with op.batch_alter_table("transactions") as batch_op:
        batch_op.alter_column(
            "dedup_key", existing_type=sa.String(), nullable=False
        )
        batch_op.create_unique_constraint(
            "uq_transactions_dedup_key", ["dedup_key"]
        )
        batch_op.create_unique_constraint(
            "uq_transactions_tx_hash_log_index", ["tx_hash", "log_index"]
        )

    # 4. Drop the legacy chain_states table (cursor now lives in Redis)
    op.drop_table("chain_states")


def downgrade() -> None:
    """Downgrade database schema.

    Revert changes to move database schema backward.
    Use with caution in production.
    """
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.drop_constraint("uq_transactions_tx_hash_log_index", type_="unique")
        batch_op.drop_constraint("uq_transactions_dedup_key", type_="unique")
        batch_op.drop_column("value_raw")
        batch_op.drop_column("token_contract_address")
        batch_op.drop_column("dedup_key")
        batch_op.drop_column("log_index")
        batch_op.create_unique_constraint("uq_transactions_tx_hash", ["tx_hash"])

    with op.batch_alter_table("payments") as batch_op:
        batch_op.drop_index("ix_payments_chain_id")
        batch_op.drop_column("chain_id")

    op.create_table(
        "chain_states",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chain", sa.String(), nullable=False),
        sa.Column("last_scanned_block", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chain", name="uq_chain_states_chain"),
    )
    with op.batch_alter_table("chain_states", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_chain_states_id"), ["id"], unique=False
        )
