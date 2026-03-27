"""add permissions tables

Revision ID: 20260327_permissions
Revises: 20260327_aws_env_config
Create Date: 2026-03-27

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260327_permissions'
down_revision = '20260327_aws_env_config'
branch_labels = None
depends_on = None


def upgrade():
    # 创建权限表
    op.create_table(
        'permissions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(100), nullable=False, comment='权限编码'),
        sa.Column('name', sa.String(100), nullable=False, comment='权限名称'),
        sa.Column('category', sa.String(50), comment='权限类别'),
        sa.Column('module', sa.String(50), comment='所属模块'),
        sa.Column('description', sa.String(200), comment='描述'),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('sort_order', sa.Integer(), server_default='0'),
        sa.Column('is_enabled', sa.Boolean(), server_default='1'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
        sa.ForeignKeyConstraint(['parent_id'], ['permissions.id'], ondelete='SET NULL')
    )
    op.create_index('ix_permissions_code', 'permissions', ['code'])
    
    # 创建角色权限关联表
    op.create_table(
        'role_permissions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('role', sa.String(50), nullable=False, comment='角色'),
        sa.Column('permission_id', sa.Integer(), nullable=False, comment='权限ID'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE')
    )
    op.create_index('ix_role_permissions_role', 'role_permissions', ['role'])
    
    # 创建批量操作日志表
    op.create_table(
        'batch_operation_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='操作人ID'),
        sa.Column('username', sa.String(50), comment='操作人用户名'),
        sa.Column('operation_type', sa.String(50), nullable=False, comment='操作类型'),
        sa.Column('resource_type', sa.String(50), nullable=False, comment='资源类型'),
        sa.Column('resource_ids', sa.JSON(), comment='资源ID列表'),
        sa.Column('total_count', sa.Integer(), server_default='0'),
        sa.Column('success_count', sa.Integer(), server_default='0'),
        sa.Column('failed_count', sa.Integer(), server_default='0'),
        sa.Column('no_permission_count', sa.Integer(), server_default='0'),
        sa.Column('details', sa.JSON(), comment='详细结果'),
        sa.Column('request_ip', sa.String(50)),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'])
    )
    op.create_index('ix_batch_operation_logs_created_at', 'batch_operation_logs', ['created_at'])
    
    # 添加环境保护级别字段
    op.add_column('environments', sa.Column('protection_level', sa.Integer(), server_default='0', comment='保护级别'))


def downgrade():
    op.drop_index('ix_batch_operation_logs_created_at', 'batch_operation_logs')
    op.drop_table('batch_operation_logs')
    
    op.drop_index('ix_role_permissions_role', 'role_permissions')
    op.drop_table('role_permissions')
    
    op.drop_index('ix_permissions_code', 'permissions')
    op.drop_table('permissions')
    
    op.drop_column('environments', 'protection_level')
