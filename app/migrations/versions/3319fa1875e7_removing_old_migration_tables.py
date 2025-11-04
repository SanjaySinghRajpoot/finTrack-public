"""removing old migration tables

Revision ID: 3319fa1875e7
Revises: 10a828247997
Create Date: 2025-10-30 23:44:52.068763

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3319fa1875e7'
down_revision: Union[str, None] = '10a828247997'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop dependent tables first to avoid FK errors
    op.drop_table('credit_history')
    op.drop_table('user_feature_usage')
    op.drop_index(op.f('idx_subscription_limits_period'), table_name='subscription_limits')
    op.drop_table('subscription_limits')
    op.drop_table('plan_features')
    op.drop_table('features')
    op.drop_table('payment_transactions')
    op.drop_table('user_subscriptions')
    op.drop_table('subscriptions')
    op.drop_table('payment_plans')
    op.drop_table('plans')
    # ### end Alembic commands ###


def downgrade() -> None:
    pass
