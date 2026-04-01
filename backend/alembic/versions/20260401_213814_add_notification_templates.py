"""add_notification_templates

Revision ID: 5f8e1b4c5d6e
Revises: dcde8c174732
Create Date: 2026-04-01 21:38:14.823405+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5f8e1b4c5d6e'
down_revision: Union[str, None] = 'dcde8c174732'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级迁移 - 创建通知模板表"""
    # 检查表是否已存在
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT to_regclass('notification_templates')"))
    exists = result.scalar() is not None
    
    if not exists:
        op.create_table(
            'notification_templates',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sa.String(100), nullable=False, comment='模板名称'),
            sa.Column('description', sa.String(200), nullable=True, comment='模板描述'),
            sa.Column('notification_type', sa.String(50), nullable=False, comment='通知类型: approval/alert/scheduled_task'),
            sa.Column('sub_type', sa.String(50), nullable=True, comment='细分类型: DDL/DML/critical/warning等'),
            sa.Column('title_template', sa.String(200), nullable=False, comment='标题模板'),
            sa.Column('content_template', sa.Text(), nullable=False, comment='内容模板(Markdown)'),
            sa.Column('variables', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='可用变量列表'),
            sa.Column('is_enabled', sa.Boolean(), nullable=True, server_default=sa.text('true'), comment='是否启用'),
            sa.Column('is_default', sa.Boolean(), nullable=True, server_default=sa.text('false'), comment='是否默认模板'),
            sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
            sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name')
        )
        op.create_index('ix_notification_templates_id', 'notification_templates', ['id'], unique=False)


def downgrade() -> None:
    """降级迁移"""
    op.drop_index('ix_notification_templates_id', table_name='notification_templates')
    op.drop_table('notification_templates')
