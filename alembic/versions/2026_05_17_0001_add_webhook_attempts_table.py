"""Add webhook_attempts table

Revision ID: a1b2c3d4e5f6
Revises: 5ec6405addd0
Create Date: 2026-05-17 00:01:00.000000

"""
# pylint: disable=invalid-name,no-member
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '5ec6405addd0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create webhook_attempts table."""
    op.create_table(
        'webhook_attempts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('payment_id', sa.String(), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('webhook_url', sa.String(), nullable=False),
        sa.Column('payload', sa.Text(), nullable=False),
        sa.Column('webhook_secret', sa.String(), nullable=True),
        sa.Column(
            'status',
            sa.Enum('pending', 'success', 'failed', name='webhookattemptstatuse'),
            nullable=False,
        ),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('next_retry_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_webhook_attempts_payment_id', 'webhook_attempts', ['payment_id'])
    op.create_index('ix_webhook_attempts_status', 'webhook_attempts', ['status'])
    op.create_index('ix_webhook_attempts_next_retry_at', 'webhook_attempts', ['next_retry_at'])


def downgrade() -> None:
    """Drop webhook_attempts table."""
    op.drop_index('ix_webhook_attempts_next_retry_at', table_name='webhook_attempts')
    op.drop_index('ix_webhook_attempts_status', table_name='webhook_attempts')
    op.drop_index('ix_webhook_attempts_payment_id', table_name='webhook_attempts')
    op.drop_table('webhook_attempts')
    op.execute("DROP TYPE IF EXISTS webhookattemptstatuse")
