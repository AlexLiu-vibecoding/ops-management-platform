"""add alert aggregation and escalation

Revision ID: 20260401_alert_aggregation
Revises: 20260401_213814_add_notification_templates
Create Date: 2026-04-01 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260401_alert_aggregation'
down_revision = '20260401_213814_add_notification_templates'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建告警聚合规则表
    op.create_table(
        'alert_aggregation_rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False, comment='规则名称'),
        sa.Column('description', sa.String(200), comment='规则描述'),
        sa.Column('metric_type', sa.String(32), comment='指标类型，空表示所有类型'),
        sa.Column('alert_level', sa.String(16), comment='告警级别，空表示所有级别'),
        sa.Column('rdb_instance_id', sa.Integer(), comment='RDB实例ID，空表示所有'),
        sa.Column('redis_instance_id', sa.Integer(), comment='Redis实例ID，空表示所有'),
        sa.Column('aggregation_window', sa.Integer(), server_default='300', comment='聚合时间窗口(秒)'),
        sa.Column('min_alert_count', sa.Integer(), server_default='2', comment='最小告警数量才聚合'),
        sa.Column('aggregation_method', sa.String(20), server_default='count', comment='聚合方法: count/summary'),
        sa.Column('is_enabled', sa.Boolean(), server_default='1', comment='是否启用'),
        sa.Column('priority', sa.Integer(), server_default='0', comment='优先级(数字越大优先级越高)'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.ForeignKeyConstraint(['rdb_instance_id'], ['rdb_instances.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['redis_instance_id'], ['redis_instances.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_alert_aggregation_rules_id', 'alert_aggregation_rules', ['id'])
    op.create_index('ix_alert_aggregation_rules_is_enabled', 'alert_aggregation_rules', ['is_enabled'])
    
    # 创建告警聚合记录表
    op.create_table(
        'alert_aggregations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('rule_id', sa.Integer(), nullable=False, comment='规则ID'),
        sa.Column('metric_type', sa.String(32), comment='指标类型'),
        sa.Column('alert_level', sa.String(16), comment='告警级别'),
        sa.Column('rdb_instance_id', sa.Integer(), comment='RDB实例ID'),
        sa.Column('redis_instance_id', sa.Integer(), comment='Redis实例ID'),
        sa.Column('alert_count', sa.Integer(), server_default='1', comment='告警数量'),
        sa.Column('alert_ids', postgresql.JSON(astext_type=sa.Text()), comment='告警ID列表'),
        sa.Column('aggregated_content', sa.Text(), comment='聚合后的内容'),
        sa.Column('notification_sent', sa.Boolean(), server_default='0', comment='是否已发送通知'),
        sa.Column('started_at', sa.DateTime(), nullable=False, comment='聚合开始时间'),
        sa.Column('ended_at', sa.DateTime(), comment='聚合结束时间'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), comment='创建时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['rule_id'], ['alert_aggregation_rules.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['rdb_instance_id'], ['rdb_instances.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['redis_instance_id'], ['redis_instances.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_alert_aggregations_id', 'alert_aggregations', ['id'])
    op.create_index('ix_alert_aggregations_rule_id', 'alert_aggregations', ['rule_id'])
    op.create_index('ix_alert_aggregations_started_at', 'alert_aggregations', ['started_at'])
    
    # 创建告警静默规则表
    op.create_table(
        'alert_silence_rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False, comment='规则名称'),
        sa.Column('description', sa.String(200), comment='规则描述'),
        sa.Column('silence_type', sa.String(20), server_default='once', comment='静默类型: once/daily/weekly'),
        sa.Column('metric_type', sa.String(32), comment='指标类型，空表示所有类型'),
        sa.Column('alert_level', sa.String(16), comment='告警级别，空表示所有级别'),
        sa.Column('rdb_instance_id', sa.Integer(), comment='RDB实例ID，空表示所有'),
        sa.Column('redis_instance_id', sa.Integer(), comment='Redis实例ID，空表示所有'),
        sa.Column('start_time', sa.String(5), comment='开始时间 HH:MM'),
        sa.Column('end_time', sa.String(5), comment='结束时间 HH:MM'),
        sa.Column('weekdays', postgresql.JSON(astext_type=sa.Text()), comment='允许的星期几 [0-6]，0=周一'),
        sa.Column('start_date', sa.DateTime(), comment='生效开始日期'),
        sa.Column('end_date', sa.DateTime(), comment='生效结束日期'),
        sa.Column('is_enabled', sa.Boolean(), server_default='1', comment='是否启用'),
        sa.Column('created_by', sa.Integer(), comment='创建人ID'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['rdb_instance_id'], ['rdb_instances.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['redis_instance_id'], ['redis_instances.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_alert_silence_rules_id', 'alert_silence_rules', ['id'])
    op.create_index('ix_alert_silence_rules_is_enabled', 'alert_silence_rules', ['is_enabled'])
    
    # 创建告警升级规则表
    op.create_table(
        'alert_escalation_rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False, comment='规则名称'),
        sa.Column('description', sa.String(200), comment='规则描述'),
        sa.Column('metric_type', sa.String(32), comment='指标类型，空表示所有类型'),
        sa.Column('alert_level', sa.String(16), comment='告警级别，空表示所有级别'),
        sa.Column('rdb_instance_id', sa.Integer(), comment='RDB实例ID，空表示所有'),
        sa.Column('redis_instance_id', sa.Integer(), comment='Redis实例ID，空表示所有'),
        sa.Column('escalation_wait_minutes', sa.Integer(), server_default='30', comment='等待多少分钟后升级'),
        sa.Column('target_alert_level', sa.String(16), comment='目标告警级别'),
        sa.Column('additional_notify_channels', sa.String(500), comment='额外通知通道ID列表(逗号分隔)'),
        sa.Column('escalation_message', sa.String(500), comment='升级消息内容'),
        sa.Column('is_enabled', sa.Boolean(), server_default='1', comment='是否启用'),
        sa.Column('created_by', sa.Integer(), comment='创建人ID'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['rdb_instance_id'], ['rdb_instances.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['redis_instance_id'], ['redis_instances.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_alert_escalation_rules_id', 'alert_escalation_rules', ['id'])
    op.create_index('ix_alert_escalation_rules_is_enabled', 'alert_escalation_rules', ['is_enabled'])


def downgrade() -> None:
    op.drop_index('ix_alert_escalation_rules_is_enabled', 'alert_escalation_rules')
    op.drop_index('ix_alert_escalation_rules_id', 'alert_escalation_rules')
    op.drop_table('alert_escalation_rules')
    
    op.drop_index('ix_alert_silence_rules_is_enabled', 'alert_silence_rules')
    op.drop_index('ix_alert_silence_rules_id', 'alert_silence_rules')
    op.drop_table('alert_silence_rules')
    
    op.drop_index('ix_alert_aggregations_started_at', 'alert_aggregations')
    op.drop_index('ix_alert_aggregations_rule_id', 'alert_aggregations')
    op.drop_index('ix_alert_aggregations_id', 'alert_aggregations')
    op.drop_table('alert_aggregations')
    
    op.drop_index('ix_alert_aggregation_rules_is_enabled', 'alert_aggregation_rules')
    op.drop_index('ix_alert_aggregation_rules_id', 'alert_aggregation_rules')
    op.drop_table('alert_aggregation_rules')
