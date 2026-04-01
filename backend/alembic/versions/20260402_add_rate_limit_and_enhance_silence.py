"""add rate limit and enhance silence rules

Revision ID: 20260402_rate_limit
Revises: 20260401_add_alert_aggregation_escalation
Create Date: 2026-04-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260402_rate_limit'
down_revision = '20260401_add_alert_aggregation_escalation'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 增强 alert_silence_rules 表
    # 添加新字段
    op.add_column('alert_silence_rules', sa.Column('silence_type', sa.String(20), server_default='once', comment='静默类型: once/daily/weekly'))
    op.add_column('alert_silence_rules', sa.Column('time_start', sa.String(5), comment='开始时间 HH:MM'))
    op.add_column('alert_silence_rules', sa.Column('time_end', sa.String(5), comment='结束时间 HH:MM'))
    op.add_column('alert_silence_rules', sa.Column('weekdays', postgresql.JSON(astext_type=sa.Text()), comment='允许的星期几 [0-6]，0=周一'))
    op.add_column('alert_silence_rules', sa.Column('start_date', sa.DateTime(), comment='生效开始日期'))
    op.add_column('alert_silence_rules', sa.Column('end_date', sa.DateTime(), comment='生效结束日期'))
    op.add_column('alert_silence_rules', sa.Column('created_by', sa.Integer(), comment='创建人ID'))
    
    # 添加外键约束
    op.create_foreign_key(
        'alert_silence_rules_created_by_fkey',
        'alert_silence_rules',
        'users',
        ['created_by'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # 数据迁移：将旧字段数据迁移到新字段
    # 将 start_time 重命名为 start_date，end_time 重命名为 end_date
    op.execute("""
        UPDATE alert_silence_rules
        SET start_date = start_time,
            end_date = end_time,
            silence_type = COALESCE(recurrence_type, 'once')
        WHERE start_time IS NOT NULL
    """)
    
    # 删除旧字段
    op.drop_column('alert_silence_rules', 'start_time')
    op.drop_column('alert_silence_rules', 'end_time')
    op.drop_column('alert_silence_rules', 'recurrence_type')
    
    # 2. 创建 alert_rate_limit_rules 表
    op.create_table(
        'alert_rate_limit_rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False, comment='规则名称'),
        sa.Column('description', sa.String(200), comment='规则描述'),
        
        # 匹配条件
        sa.Column('metric_type', sa.String(32), comment='指标类型'),
        sa.Column('alert_level', sa.String(16), comment='告警级别'),
        sa.Column('rdb_instance_id', sa.Integer(), comment='RDB实例ID'),
        sa.Column('redis_instance_id', sa.Integer(), comment='Redis实例ID'),
        
        # 频率限制配置
        sa.Column('limit_window', sa.Integer(), server_default='300', comment='限制时间窗口(秒)'),
        sa.Column('max_notifications', sa.Integer(), server_default='5', comment='时间窗口内最大通知数量'),
        sa.Column('cooldown_period', sa.Integer(), server_default='600', comment='冷却期(秒)'),
        
        # 状态和创建信息
        sa.Column('is_enabled', sa.Boolean(), server_default='1', comment='是否启用'),
        sa.Column('priority', sa.Integer(), server_default='0', comment='优先级'),
        sa.Column('created_by', sa.Integer(), comment='创建人ID'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), comment='更新时间'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['rdb_instance_id'], ['rdb_instances.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['redis_instance_id'], ['redis_instances.id'], ondelete='CASCADE'),
    )
    
    # 创建索引
    op.create_index('ix_alert_rate_limit_rules_id', 'alert_rate_limit_rules', ['id'])
    op.create_index('ix_alert_rate_limit_rules_is_enabled', 'alert_rate_limit_rules', ['is_enabled'])


def downgrade() -> None:
    # 1. 删除 alert_rate_limit_rules 表
    op.drop_index('ix_alert_rate_limit_rules_is_enabled', 'alert_rate_limit_rules')
    op.drop_index('ix_alert_rate_limit_rules_id', 'alert_rate_limit_rules')
    op.drop_table('alert_rate_limit_rules')
    
    # 2. 恢复 alert_silence_rules 表的旧结构
    op.add_column('alert_silence_rules', sa.Column('start_time', sa.DateTime(), comment='静默开始时间'))
    op.add_column('alert_silence_rules', sa.Column('end_time', sa.DateTime(), comment='静默结束时间'))
    op.add_column('alert_silence_rules', sa.Column('recurrence_type', sa.String(20), server_default='once', comment='重复类型'))
    
    # 数据迁移：将新字段数据迁移回旧字段
    op.execute("""
        UPDATE alert_silence_rules
        SET start_time = start_date,
            end_time = end_date,
            recurrence_type = silence_type
    """)
    
    # 删除新字段
    op.drop_constraint('alert_silence_rules_created_by_fkey', 'alert_silence_rules', type_='foreignkey')
    op.drop_column('alert_silence_rules', 'silence_type')
    op.drop_column('alert_silence_rules', 'time_start')
    op.drop_column('alert_silence_rules', 'time_end')
    op.drop_column('alert_silence_rules', 'weekdays')
    op.drop_column('alert_silence_rules', 'start_date')
    op.drop_column('alert_silence_rules', 'end_date')
    op.drop_column('alert_silence_rules', 'created_by')
