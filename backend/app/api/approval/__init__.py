"""
变更审批API模块

将原有的 approval.py (1291行) 拆分为以下模块：
- helpers.py: 辅助函数
- rollback.py: 回滚生成
- endpoints.py: API端点

每个模块职责单一，便于维护和测试。
"""
from fastapi import APIRouter

from .endpoints import router

# 导出主路由
__all__ = ["router"]

# 保持向后兼容，导出为 router
approval_router = router
