"""add aws config to environments

Revision ID: aws_env_config_001
Revises: 9103b4f35d0e
Create Date: 2024-03-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aws_env_config_001'
down_revision: Union[str, None] = '9103b4f35d0e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级迁移：添加 AWS 配置字段到 environments 表"""
    # 添加 AWS 区域字段
    op.add_column('environments', sa.Column('aws_region', sa.String(50), nullable=True, comment='AWS 区域'))
    
    # 添加 AWS Access Key ID
    op.add_column('environments', sa.Column('aws_access_key_id', sa.String(100), nullable=True, comment='AWS Access Key ID'))
    
    # 添加 AWS Secret Access Key
    op.add_column('environments', sa.Column('aws_secret_access_key', sa.String(100), nullable=True, comment='AWS Secret Access Key (加密存储)'))
    
    # 添加 AWS 配置状态标记
    op.add_column('environments', sa.Column('aws_configured', sa.Boolean(), nullable=True, default=False, comment='AWS 凭证是否已配置'))


def downgrade() -> None:
    """回滚迁移：移除 AWS 配置字段"""
    op.drop_column('environments', 'aws_configured')
    op.drop_column('environments', 'aws_secret_access_key')
    op.drop_column('environments', 'aws_access_key_id')
    op.drop_column('environments', 'aws_region')
