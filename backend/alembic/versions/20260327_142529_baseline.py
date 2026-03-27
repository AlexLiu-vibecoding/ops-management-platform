"""baseline

Revision ID: 9103b4f35d0e
Revises: 
Create Date: 2026-03-27 14:25:29.907591+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9103b4f35d0e'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级迁移"""
    pass


def downgrade() -> None:
    """回滚迁移"""
    pass
