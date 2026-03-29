"""add scheduled inspection, alert rules, change windows

Revision ID: 20260329_inspection_alert
Revises: 20260328_role_environments
Create Date: 2026-03-29 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260329_inspection_alert'
down_revision = '20260328_role_environments'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建定时巡检任务表
    op.create_table(
        'scheduled_inspections',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False, comment='任务名称'),
        sa.Column('description', sa.String(500), comment='描述'),
        sa.Column('instance_scope', sa.String(20), server_default='all', comment='实例范围: all/selected'),
        sa.Column('instance_ids', postgresql.JSON(astext_type=sa.Text()), comment='选中的实例ID列表'),
        sa.Column('modules', postgresql.JSON(astext_type=sa.Text()), comment='检查模块列表'),
        sa.Column('cron_expression', sa.String(100), nullable=False, comment='Cron表达式'),
        sa.Column('timezone', sa.String(50), server_default='Asia/Shanghai', comment='时区'),
        sa.Column('status', sa.String(20), server_default='enabled', comment='状态'),
        sa.Column('last_run_time', sa.DateTime(), comment='上次执行时间'),
        sa.Column('last_run_status', sa.String(20), comment='上次执行状态'),
        sa.Column('next_run_time', sa.DateTime(), comment='下次执行时间'),
        sa.Column('run_count', sa.Integer(), server_default='0', comment='执行次数'),
        sa.Column('success_count', sa.Integer(), server_default='0', comment='成功次数'),
        sa.Column('fail_count', sa.Integer(), server_default='0', comment='失败次数'),
        sa.Column('notify_on_complete', sa.Boolean(), server_default='1', comment='完成时通知'),
        sa.Column('notify_on_warning', sa.Boolean(), server_default='1', comment='发现警告时通知'),
        sa.Column('notify_on_critical', sa.Boolean(), server_default='1', comment='发现严重问题时通知'),
        sa.Column('notify_channels', sa.String(500), comment='通知通道ID列表'),
        sa.Column('created_by', sa.Integer(), comment='创建人ID'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_scheduled_inspections_status', 'scheduled_inspections', ['status'])
    
    # 创建巡检执行记录表
    op.create_table(
        'inspection_executions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('scheduled_inspection_id', sa.Integer(), comment='定时巡检ID'),
        sa.Column('trigger_type', sa.String(20), server_default='scheduled', comment='触发类型'),
        sa.Column('start_time', sa.DateTime(), comment='开始时间'),
        sa.Column('end_time', sa.DateTime(), comment='结束时间'),
        sa.Column('duration', sa.Integer(), comment='执行时长(秒)'),
        sa.Column('status', sa.String(20), server_default='running', comment='状态'),
        sa.Column('total_instances', sa.Integer(), server_default='0', comment='检查的实例总数'),
        sa.Column('normal_count', sa.Integer(), server_default='0', comment='正常数量'),
        sa.Column('warning_count', sa.Integer(), server_default='0', comment='警告数量'),
        sa.Column('critical_count', sa.Integer(), server_default='0', comment='严重数量'),
        sa.Column('error_count', sa.Integer(), server_default='0', comment='错误数量'),
        sa.Column('summary', postgresql.JSON(astext_type=sa.Text()), comment='结果摘要'),
        sa.Column('details', postgresql.JSON(astext_type=sa.Text()), comment='详细结果'),
        sa.Column('error_message', sa.Text(), comment='错误信息'),
        sa.Column('triggered_by', sa.Integer(), comment='触发人ID'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), comment='创建时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['scheduled_inspection_id'], ['scheduled_inspections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['triggered_by'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_inspection_executions_created_at', 'inspection_executions', ['created_at'])
    
    # 创建告警规则表
    op.create_table(
        'alert_rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False, comment='规则名称'),
        sa.Column('description', sa.String(500), comment='描述'),
        sa.Column('rule_type', sa.String(50), nullable=False, comment='规则类型'),
        sa.Column('instance_scope', sa.String(20), server_default='all', comment='实例范围'),
        sa.Column('instance_ids', postgresql.JSON(astext_type=sa.Text()), comment='选中的实例ID列表'),
        sa.Column('environment_ids', postgresql.JSON(astext_type=sa.Text()), comment='选中的环境ID列表'),
        sa.Column('metric_name', sa.String(100), comment='指标名称'),
        sa.Column('operator', sa.String(10), server_default='>', comment='比较运算符'),
        sa.Column('threshold', sa.Float(), comment='阈值'),
        sa.Column('duration', sa.Integer(), server_default='60', comment='持续时间(秒)'),
        sa.Column('aggregation', sa.String(20), server_default='avg', comment='聚合方式'),
        sa.Column('severity', sa.String(20), server_default='warning', comment='告警级别'),
        sa.Column('silence_duration', sa.Integer(), server_default='300', comment='静默时长(秒)'),
        sa.Column('silence_until', sa.DateTime(), comment='静默截止时间'),
        sa.Column('notify_channels', sa.String(500), comment='通知通道ID列表'),
        sa.Column('notify_enabled', sa.Boolean(), server_default='1', comment='是否启用通知'),
        sa.Column('is_enabled', sa.Boolean(), server_default='1', comment='是否启用'),
        sa.Column('last_triggered_at', sa.DateTime(), comment='上次触发时间'),
        sa.Column('trigger_count', sa.Integer(), server_default='0', comment='触发次数'),
        sa.Column('created_by', sa.Integer(), comment='创建人ID'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_alert_rules_is_enabled', 'alert_rules', ['is_enabled'])
    op.create_index('ix_alert_rules_rule_type', 'alert_rules', ['rule_type'])
    
    # 创建变更时间窗口表
    op.create_table(
        'change_windows',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False, comment='窗口名称'),
        sa.Column('description', sa.String(500), comment='描述'),
        sa.Column('environment_id', sa.Integer(), comment='环境ID'),
        sa.Column('weekdays', postgresql.JSON(astext_type=sa.Text()), comment='允许的星期几'),
        sa.Column('start_time', sa.Time(), comment='开始时间'),
        sa.Column('end_time', sa.Time(), comment='结束时间'),
        sa.Column('cross_day', sa.Boolean(), server_default='0', comment='是否跨天'),
        sa.Column('window_type', sa.String(20), server_default='allowed', comment='窗口类型'),
        sa.Column('is_enabled', sa.Boolean(), server_default='1', comment='是否启用'),
        sa.Column('priority', sa.Integer(), server_default='0', comment='优先级'),
        sa.Column('created_by', sa.Integer(), comment='创建人ID'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['environment_id'], ['environments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_change_windows_is_enabled', 'change_windows', ['is_enabled'])
    op.create_index('ix_change_windows_environment_id', 'change_windows', ['environment_id'])


def downgrade() -> None:
    op.drop_index('ix_change_windows_environment_id', 'change_windows')
    op.drop_index('ix_change_windows_is_enabled', 'change_windows')
    op.drop_table('change_windows')
    
    op.drop_index('ix_alert_rules_rule_type', 'alert_rules')
    op.drop_index('ix_alert_rules_is_enabled', 'alert_rules')
    op.drop_table('alert_rules')
    
    op.drop_index('ix_inspection_executions_created_at', 'inspection_executions')
    op.drop_table('inspection_executions')
    
    op.drop_index('ix_scheduled_inspections_status', 'scheduled_inspections')
    op.drop_table('scheduled_inspections')
