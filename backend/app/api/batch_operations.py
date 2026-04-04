"""
批量操作 API

支持实例、环境、变更的批量操作，包含权限校验
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, RDBInstance, RedisInstance, Environment, ApprovalRecord, ApprovalStatus
from app.deps import get_current_user
from app.services.permission_service import PermissionService, BatchOperationService
from app.models.permissions import PermissionCode

router = APIRouter(prefix="/batch", tags=["批量操作"])


# ==================== 请求模型 ====================

class BatchOperationRequest(BaseModel):
    """批量操作请求"""
    action: str  # delete, enable, disable, approve, reject
    ids: list[int]
    params: Optional[dict] = None  # 额外参数


class BatchOperationResponse(BaseModel):
    """批量操作响应"""
    success: bool
    total: int
    succeeded: int
    failed: int
    no_permission: int
    results: list[dict] = []  # 可选的详细结果列表


# ==================== 实例批量操作 ====================

@router.post("/instances", response_model=BatchOperationResponse)
async def batch_instances_operation(
    request: Request,
    body: BatchOperationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    批量实例操作
    
    - delete: 批量删除
    - enable: 批量启用
    - disable: 批量停用
    """
    perm_service = PermissionService(db)
    batch_service = BatchOperationService(db, perm_service)
    
    # 1. 功能权限检查
    action_permission_map = {
        "delete": PermissionCode.INSTANCE_BATCH_DELETE,
        "enable": PermissionCode.INSTANCE_BATCH_ENABLE,
        "disable": PermissionCode.INSTANCE_BATCH_DISABLE,
    }
    
    permission_code = action_permission_map.get(body.action)
    if not permission_code:
        raise HTTPException(status_code=400, detail=f"不支持的操作: {body.action}")
    
    perm_service.check_permission(current_user, permission_code)
    
    # 2. 获取实例列表（RDB + Redis）
    rdb_instances = db.query(RDBInstance).filter(RDBInstance.id.in_(body.ids)).all()
    redis_instances = db.query(RedisInstance).filter(RedisInstance.id.in_(body.ids)).all()
    all_instances = list(rdb_instances) + list(redis_instances)
    
    # 3. 数据权限过滤
    accessible_envs = perm_service.get_user_environment_ids(current_user)
    
    results = {
        "total": len(body.ids),
        "succeeded": 0,
        "failed": 0,
        "no_permission": 0,
        "results": []
    }
    
    # 4. 逐个处理
    for instance in all_instances:
        instance_type = "rdb" if isinstance(instance, RDBInstance) else "redis"
        
        # 数据权限检查
        if instance.environment_id not in accessible_envs:
            results["no_permission"] += 1
            results["results"].append({
                "id": instance.id,
                "name": instance.name,
                "type": instance_type,
                "status": "no_permission",
                "reason": "无此环境的访问权限"
            })
            continue
        
        # 保护级别检查
        allowed, reason = perm_service.check_batch_operation_allowed(
            current_user, instance.environment_id, len(body.ids)
        )
        if not allowed:
            results["failed"] += 1
            results["results"].append({
                "id": instance.id,
                "name": instance.name,
                "type": instance_type,
                "status": "blocked",
                "reason": reason
            })
            continue
        
        # 执行操作
        try:
            if body.action == "delete":
                db.delete(instance)
            elif body.action == "enable":
                instance.status = True
            elif body.action == "disable":
                instance.status = False
            
            results["succeeded"] += 1
            results["results"].append({
                "id": instance.id,
                "name": instance.name,
                "type": instance_type,
                "status": "success"
            })
        except Exception as e:
            results["failed"] += 1
            results["results"].append({
                "id": instance.id,
                "name": instance.name,
                "type": instance_type,
                "status": "failed",
                "reason": str(e)
            })
    
    db.commit()
    
    # 5. 记录日志
    batch_service.log_batch_operation(
        user=current_user,
        operation_type=f"instance_{body.action}",
        resource_type="instance",
        resource_ids=body.ids,
        results=results,
        request_ip=request.client.host if request.client else None
    )
    
    return BatchOperationResponse(
        success=results["failed"] == 0,
        **results
    )


# ==================== 环境批量操作 ====================

@router.post("/environments", response_model=BatchOperationResponse)
async def batch_environments_operation(
    request: Request,
    body: BatchOperationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    批量环境操作
    
    - delete: 批量删除
    - enable: 批量启用
    - disable: 批量停用
    """
    perm_service = PermissionService(db)
    batch_service = BatchOperationService(db, perm_service)
    
    # 1. 功能权限检查
    action_permission_map = {
        "delete": PermissionCode.ENVIRONMENT_BATCH_DELETE,
        "enable": PermissionCode.ENVIRONMENT_UPDATE,
        "disable": PermissionCode.ENVIRONMENT_UPDATE,
    }
    
    permission_code = action_permission_map.get(body.action)
    if not permission_code:
        raise HTTPException(status_code=400, detail=f"不支持的操作: {body.action}")
    
    perm_service.check_permission(current_user, permission_code)
    
    # 2. 获取环境列表
    environments = db.query(Environment).filter(Environment.id.in_(body.ids)).all()
    
    results = {
        "total": len(body.ids),
        "succeeded": 0,
        "failed": 0,
        "no_permission": 0,
        "details": []
    }
    
    # 3. 逐个处理
    for env in environments:
        # 检查是否有实例关联
        rdb_count = db.query(RDBInstance).filter(RDBInstance.environment_id == env.id).count()
        redis_count = db.query(RedisInstance).filter(RedisInstance.environment_id == env.id).count()
        
        if body.action == "delete" and (rdb_count > 0 or redis_count > 0):
            results["failed"] += 1
            results["results"].append({
                "id": env.id,
                "name": env.name,
                "status": "blocked",
                "reason": f"环境下有 {rdb_count + redis_count} 个实例，无法删除"
            })
            continue
        
        try:
            if body.action == "delete":
                db.delete(env)
            elif body.action == "enable":
                env.status = True
            elif body.action == "disable":
                env.status = False
            
            results["succeeded"] += 1
            results["results"].append({
                "id": env.id,
                "name": env.name,
                "status": "success"
            })
        except Exception as e:
            results["failed"] += 1
            results["results"].append({
                "id": env.id,
                "name": env.name,
                "status": "failed",
                "reason": str(e)
            })
    
    db.commit()
    
    # 4. 记录日志
    batch_service.log_batch_operation(
        user=current_user,
        operation_type=f"environment_{body.action}",
        resource_type="environment",
        resource_ids=body.ids,
        results=results,
        request_ip=request.client.host if request.client else None
    )
    
    return BatchOperationResponse(
        success=results["failed"] == 0,
        **results
    )


# ==================== 变更批量操作 ====================

@router.post("/approvals", response_model=BatchOperationResponse)
async def batch_approvals_operation(
    request: Request,
    body: BatchOperationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    批量变更操作
    
    - approve: 批量通过
    - reject: 批量拒绝
    - delete: 批量删除（只能删除自己的已拒绝/已执行的变更）
    """
    perm_service = PermissionService(db)
    batch_service = BatchOperationService(db, perm_service)
    
    # 1. 功能权限检查
    action_permission_map = {
        "approve": PermissionCode.APPROVAL_BATCH_APPROVE,
        "reject": PermissionCode.APPROVAL_BATCH_REJECT,
        "delete": PermissionCode.APPROVAL_DELETE,
    }
    
    permission_code = action_permission_map.get(body.action)
    if not permission_code:
        raise HTTPException(status_code=400, detail=f"不支持的操作: {body.action}")
    
    perm_service.check_permission(current_user, permission_code)
    
    # 2. 获取变更列表
    approvals = db.query(ApprovalRecord).filter(ApprovalRecord.id.in_(body.ids)).all()
    
    # 3. 数据权限过滤
    accessible_envs = perm_service.get_user_environment_ids(current_user)
    
    results = {
        "total": len(body.ids),
        "succeeded": 0,
        "failed": 0,
        "no_permission": 0,
        "details": []
    }
    
    # 4. 逐个处理
    for approval in approvals:
        # 数据权限检查（按环境）
        if approval.environment_id and approval.environment_id not in accessible_envs:
            results["no_permission"] += 1
            results["results"].append({
                "id": approval.id,
                "name": approval.title,
                "status": "no_permission",
                "reason": "无此环境的访问权限"
            })
            continue
        
        # 操作特定检查
        if body.action in ["approve", "reject"]:
            # 只有待审批状态可以操作
            if approval.status != ApprovalStatus.PENDING:
                results["failed"] += 1
                results["results"].append({
                    "id": approval.id,
                    "name": approval.title,
                    "status": "blocked",
                    "reason": f"状态为 {approval.status.value}，无法操作"
                })
                continue
        
        if body.action == "delete":
            # 删除权限检查：只能删除自己的或已完成的
            can_delete = (
                approval.requester_id == current_user.id or
                perm_service.has_permission(current_user, PermissionCode.APPROVAL_DELETE)
            )
            if not can_delete:
                results["no_permission"] += 1
                results["results"].append({
                    "id": approval.id,
                    "name": approval.title,
                    "status": "no_permission",
                    "reason": "无权删除此变更"
                })
                continue
            
            # 只能删除已拒绝或已执行的
            if approval.status not in [ApprovalStatus.REJECTED, ApprovalStatus.EXECUTED, ApprovalStatus.FAILED]:
                results["failed"] += 1
                results["results"].append({
                    "id": approval.id,
                    "name": approval.title,
                    "status": "blocked",
                    "reason": "只能删除已拒绝/已执行/失败的变更"
                })
                continue
        
        # 执行操作
        try:
            if body.action == "approve":
                approval.status = ApprovalStatus.APPROVED
                approval.approver_id = current_user.id
                # 如果是自动执行，触发执行
                if approval.auto_execute:
                    # TODO: 触发异步执行
                    pass
            elif body.action == "reject":
                approval.status = ApprovalStatus.REJECTED
                approval.approver_id = current_user.id
            elif body.action == "delete":
                db.delete(approval)
            
            results["succeeded"] += 1
            results["results"].append({
                "id": approval.id,
                "name": approval.title,
                "status": "success"
            })
        except Exception as e:
            results["failed"] += 1
            results["results"].append({
                "id": approval.id,
                "name": approval.title,
                "status": "failed",
                "reason": str(e)
            })
    
    db.commit()
    
    # 5. 记录日志
    batch_service.log_batch_operation(
        user=current_user,
        operation_type=f"approval_{body.action}",
        resource_type="approval",
        resource_ids=body.ids,
        results=results,
        request_ip=request.client.host if request.client else None
    )
    
    return BatchOperationResponse(
        success=results["failed"] == 0,
        **results
    )


# ==================== 获取用户权限 ====================

@router.get("/permissions")
async def get_user_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前用户的权限列表"""
    perm_service = PermissionService(db)
    
    permissions = perm_service.get_role_permissions(current_user.role)
    env_ids = perm_service.get_user_environment_ids(current_user)
    
    return {
        "role": current_user.role.value,
        "permissions": list(permissions),
        "environment_ids": list(env_ids)
    }
