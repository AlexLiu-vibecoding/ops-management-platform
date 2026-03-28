"""add role_environments table and migrate data

Revision ID: 20260328_role_environments
Revises: 20260327_permissions
Create Date: 2026-03-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '20260328_role_environments'
down_revision = '20260327_permissions'
branch_labels = None
depends_on = None


def upgrade():
    # 创建角色-环境关联表
    op.create_table(
        'role_environments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('role', sa.String(50), nullable=False, comment='角色'),
        sa.Column('environment_id', sa.Integer(), nullable=False, comment='环境ID'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['environment_id'], ['environments.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('role', 'environment_id', name='uq_role_environment')
    )
    op.create_index('ix_role_environments_role', 'role_environments', ['role'])
    
    # 获取数据库连接
    conn = op.get_bind()
    
    # 获取所有环境
    environments = conn.execute(text("SELECT id FROM environments WHERE status = true")).fetchall()
    env_ids = [e[0] for e in environments]
    
    # 默认角色环境权限配置
    # super_admin 和 approval_admin：所有环境
    # operator：除生产外的所有环境
    # developer：测试和开发环境
    # readonly：仅测试环境
    
    if env_ids:
        # 获取环境编码，用于判断环境类型
        env_info = conn.execute(text("SELECT id, code FROM environments")).fetchall()
        env_code_map = {e[0]: e[1] for e in env_info}
        
        role_env_bindings = []
        
        for env_id in env_ids:
            env_code = env_code_map.get(env_id, '')
            
            # super_admin 和 approval_admin：所有环境
            role_env_bindings.append(('super_admin', env_id))
            role_env_bindings.append(('approval_admin', env_id))
            
            # operator：除生产外的所有环境
            if env_code != 'production':
                role_env_bindings.append(('operator', env_id))
            
            # developer：测试和开发环境
            if env_code in ('development', 'testing'):
                role_env_bindings.append(('developer', env_id))
            
            # readonly：仅测试环境
            if env_code == 'testing':
                role_env_bindings.append(('readonly', env_id))
        
        # 批量插入角色环境关联
        for role, env_id in role_env_bindings:
            conn.execute(
                text("INSERT INTO role_environments (role, environment_id, created_at) VALUES (:role, :env_id, NOW())"),
                {"role": role, "env_id": env_id}
            )
    
    # 保留 user_environments 表作为历史记录，但标记为已废弃
    # 后续可以删除，这里先不删，便于回滚


def downgrade():
    op.drop_index('ix_role_environments_role', 'role_environments')
    op.drop_table('role_environments')
