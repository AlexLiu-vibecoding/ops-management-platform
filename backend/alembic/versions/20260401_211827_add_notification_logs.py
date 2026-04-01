"""add_notification_logs

Revision ID: dcde8c174732
Revises: 20260329_inspection_alert
Create Date: 2026-04-01 21:18:27.785514+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'dcde8c174732'
down_revision: Union[str, None] = '20260329_inspection_alert'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级迁移 - 创建通知历史记录表"""
    # 检查表是否已存在
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT to_regclass('notification_logs')"))
    exists = result.scalar() is not None
    
    if not exists:
        op.create_table(
            'notification_logs',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('notification_type', sa.String(50), nullable=False, comment='通知类型: approval/alert/scheduled_task'),
            sa.Column('sub_type', sa.String(50), nullable=True, comment='细分类型: DDL/DML/critical/warning等'),
            sa.Column('channel_id', sa.Integer(), nullable=True, comment='通道ID'),
            sa.Column('channel_name', sa.String(100), nullable=True, comment='通道名称(冗余)'),
            sa.Column('rdb_instance_id', sa.Integer(), nullable=True, comment='RDB实例ID'),
            sa.Column('redis_instance_id', sa.Integer(), nullable=True, comment='Redis实例ID'),
            sa.Column('approval_id', sa.Integer(), nullable=True, comment='审批记录ID'),
            sa.Column('alert_id', sa.Integer(), nullable=True, comment='告警记录ID'),
            sa.Column('title', sa.String(200), nullable=False, comment='通知标题'),
            sa.Column('content', sa.Text(), nullable=True, comment='通知内容'),
            sa.Column('status', sa.String(20), nullable=True, default='pending', comment='状态: pending/success/failed'),
            sa.Column('error_message', sa.String(500), nullable=True, comment='错误信息'),
            sa.Column('response_code', sa.Integer(), nullable=True, comment='HTTP响应码'),
            sa.Column('response_data', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='响应数据'),
            sa.Column('sent_at', sa.DateTime(), nullable=True, comment='发送时间'),
            sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
            sa.ForeignKeyConstraint(['channel_id'], ['dingtalk_channels.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['rdb_instance_id'], ['rdb_instances.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['redis_instance_id'], ['redis_instances.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['approval_id'], ['approval_records.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_notification_logs_id', 'notification_logs', ['id'], unique=False)
        op.create_index('ix_notification_logs_type', 'notification_logs', ['notification_type'], unique=False)
        op.create_index('ix_notification_logs_status', 'notification_logs', ['status'], unique=False)
        op.create_index('ix_notification_logs_created_at', 'notification_logs', ['created_at'], unique=False)


def downgrade() -> None:
    """降级迁移"""
    op.drop_index('ix_notification_logs_created_at', table_name='notification_logs')
    op.drop_index('ix_notification_logs_status', table_name='notification_logs')
    op.drop_index('ix_notification_logs_type', table_name='notification_logs')
    op.drop_index('ix_notification_logs_id', table_name='notification_logs')
    op.drop_table('notification_logs')
