"""
脚本管理API
"""
import os
import json
import asyncio
import subprocess
import tempfile
import signal
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc
import httpx

from app.database import get_db
from app.models import (
    Script, ScriptExecution, ScheduledTask,
    ScriptType, ExecutionStatus, TriggerType,
    User, UserRole, DingTalkChannel
)
from app.schemas import MessageResponse
from app.deps import get_current_user
from app.utils.redis_client import redis_client
from app.utils.auth import aes_cipher
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scripts", tags=["脚本管理"])


# ==================== Schemas ====================

class ScriptCreate(BaseModel):
    """创建脚本"""
    name: str = Field(..., max_length=100)
    script_type: str = Field("python", description="python/bash/sql")
    content: str
    description: Optional[str] = None
    params_schema: Optional[Dict[str, Any]] = None
    timeout: int = Field(300, ge=1, le=3600)
    max_retries: int = Field(0, ge=0, le=10)
    is_public: bool = False
    allowed_roles: Optional[str] = None
    tags: Optional[str] = None
    # 通知配置
    notify_on_success: bool = Field(False, description="执行成功时发送通知")
    notify_on_failure: bool = Field(True, description="执行失败时发送通知")
    notify_channels: Optional[str] = Field(None, description="通知通道ID列表，逗号分隔")


class ScriptUpdate(BaseModel):
    """更新脚本"""
    name: Optional[str] = Field(None, max_length=100)
    content: Optional[str] = None
    description: Optional[str] = None
    params_schema: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = Field(None, ge=1, le=3600)
    max_retries: Optional[int] = Field(None, ge=0, le=10)
    is_enabled: Optional[bool] = None
    is_public: Optional[bool] = None
    allowed_roles: Optional[str] = None
    tags: Optional[str] = None
    # 通知配置
    notify_on_success: Optional[bool] = None
    notify_on_failure: Optional[bool] = None
    notify_channels: Optional[str] = None


class ScriptExecute(BaseModel):
    """执行脚本请求"""
    params: Optional[Dict[str, Any]] = Field(default={}, description="执行参数")
    async_exec: bool = Field(True, description="是否异步执行")
    timeout: Optional[int] = Field(None, description="超时时间（秒）")


class ExecutionQuery(BaseModel):
    """执行记录查询"""
    script_id: Optional[int] = None
    status: Optional[str] = None
    trigger_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    skip: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)


# ==================== Helper Functions ====================

def check_script_permission(script: Script, user: User) -> bool:
    """检查用户是否有权限执行脚本"""
    if user.role == UserRole.SUPER_ADMIN:
        return True
    
    if script.created_by == user.id:
        return True
    
    if script.is_public:
        return True
    
    if script.allowed_roles:
        allowed = [r.strip() for r in script.allowed_roles.split(",")]
        if user.role.value in allowed:
            return True
    
    return False


async def send_script_notification(
    db: Session,
    script: Script,
    execution: ScriptExecution,
    trigger_user: User
):
    """
    发送脚本执行通知
    
    Args:
        db: 数据库会话
        script: 脚本对象
        execution: 执行记录
        trigger_user: 触发用户
    """
    # 检查是否需要发送通知
    is_success = execution.status == ExecutionStatus.SUCCESS
    is_failure = execution.status in [ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT]
    
    if is_success and not script.notify_on_success:
        return
    if is_failure and not script.notify_on_failure:
        return
    
    # 获取通知通道
    if not script.notify_channels:
        return
    
    channel_ids = [int(cid.strip()) for cid in script.notify_channels.split(",") if cid.strip().isdigit()]
    if not channel_ids:
        return
    
    channels = db.query(DingTalkChannel).filter(
        DingTalkChannel.id.in_(channel_ids),
        DingTalkChannel.is_enabled == True
    ).all()
    
    if not channels:
        return
    
    # 构建通知内容
    status_text = {
        ExecutionStatus.SUCCESS: "✅ 成功",
        ExecutionStatus.FAILED: "❌ 失败",
        ExecutionStatus.TIMEOUT: "⏰ 超时",
        ExecutionStatus.CANCELLED: "🚫 已取消"
    }.get(execution.status, "❓ 未知")
    
    # 执行时长
    duration_text = f"{execution.duration:.2f}秒" if execution.duration else "-"
    
    # 构建消息
    content = f"""【脚本执行通知】
脚本名称：{script.name}
执行状态：{status_text}
触发人：{trigger_user.username}
触发时间：{execution.start_time.strftime('%Y-%m-%d %H:%M:%S') if execution.start_time else '-'}
执行时长：{duration_text}
"""
    
    if execution.error_output:
        content += f"\n错误信息：\n{execution.error_output}"
    
    # 发送通知
    for channel in channels:
        try:
            webhook = aes_cipher.decrypt(channel.webhook_encrypted) if channel.webhook_encrypted else None
            if not webhook:
                continue
            
            # 如果是加签验证，生成签名
            if channel.auth_type == "sign" and channel.secret_encrypted:
                import hmac
                import hashlib
                import base64
                import time
                import urllib.parse
                
                secret = aes_cipher.decrypt(channel.secret_encrypted)
                timestamp = str(round(time.time() * 1000))
                string_to_sign = f"{timestamp}\n{secret}"
                hmac_code = hmac.new(
                    secret.encode('utf-8'),
                    string_to_sign.encode('utf-8'),
                    digestmod=hashlib.sha256
                ).digest()
                sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
                separator = "&" if "?" in webhook else "?"
                webhook = f"{webhook}{separator}timestamp={timestamp}&sign={sign}"
            
            # 关键词验证
            message_content = content
            if channel.auth_type == "keyword" and channel.keywords:
                keywords = channel.keywords if isinstance(channel.keywords, list) else json.loads(channel.keywords)
                if keywords:
                    message_content = f"{content}\n{keywords[0]}"
            
            # 发送消息
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook,
                    json={"msgtype": "text", "text": {"content": message_content}},
                    timeout=10
                )
                result = response.json()
                if result.get("errcode", 0) != 0:
                    logger.warning(f"通知发送失败: {result.get('errmsg')}")
                else:
                    logger.info(f"脚本执行通知发送成功: 脚本ID={script.id}, 通道ID={channel.id}")
                    
        except Exception as e:
            logger.error(f"发送通知到通道 {channel.id} 失败: {e}")


async def execute_script_async(
    execution_id: int,
    script: Script,
    params: Dict[str, Any],
    timeout: int
):
    """
    异步执行脚本
    
    Args:
        execution_id: 执行记录ID
        script: 脚本对象
        params: 执行参数
        timeout: 超时时间
    """
    from app.database import SessionLocal
    
    db = SessionLocal()
    try:
        execution = db.query(ScriptExecution).filter(
            ScriptExecution.id == execution_id
        ).first()
        
        if not execution:
            return
        
        # 获取触发用户
        trigger_user = db.query(User).filter(User.id == execution.triggered_by).first()
        
        # 更新状态为执行中
        execution.status = ExecutionStatus.RUNNING
        execution.start_time = datetime.now()
        db.commit()
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=f'.{script.script_type.value}',
            delete=False
        ) as f:
            f.write(script.content)
            script_path = f.name
        
        # 构建执行命令
        if script.script_type == ScriptType.PYTHON:
            # 注入参数到环境变量
            env = os.environ.copy()
            env['SCRIPT_PARAMS'] = json.dumps(params)
            for key, value in params.items():
                env[f'PARAM_{key.upper()}'] = str(value)
            cmd = ['python3', script_path]
        elif script.script_type == ScriptType.BASH:
            env = os.environ.copy()
            env['SCRIPT_PARAMS'] = json.dumps(params)
            for key, value in params.items():
                env[f'PARAM_{key.upper()}'] = str(value)
            cmd = ['bash', script_path]
        else:
            execution.status = ExecutionStatus.FAILED
            execution.error_output = f"不支持的脚本类型: {script.script_type}"
            execution.end_time = datetime.now()
            db.commit()
            # 发送通知
            if trigger_user:
                await send_script_notification(db, script, execution, trigger_user)
            return
        
        try:
            # 执行脚本
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                # 更新执行结果
                execution.status = ExecutionStatus.SUCCESS if process.returncode == 0 else ExecutionStatus.FAILED
                execution.output = stdout.decode('utf-8', errors='replace')
                execution.error_output = stderr.decode('utf-8', errors='replace')
                execution.exit_code = process.returncode
                
            except asyncio.TimeoutError:
                # 超时，杀死进程
                process.kill()
                execution.status = ExecutionStatus.TIMEOUT
                execution.error_output = f"脚本执行超时（{timeout}秒）"
            
        except Exception as e:
            execution.status = ExecutionStatus.FAILED
            execution.error_output = str(e)
        
        finally:
            # 清理临时文件
            try:
                os.unlink(script_path)
            except:
                pass
        
        # 更新执行时间
        execution.end_time = datetime.now()
        if execution.start_time:
            execution.duration = (execution.end_time - execution.start_time).total_seconds()
        
        db.commit()
        
        logger.info(f"脚本执行完成: ID={execution_id}, 状态={execution.status}")
        
        # 发送通知
        if trigger_user:
            await send_script_notification(db, script, execution, trigger_user)
        
    except Exception as e:
        logger.error(f"脚本执行失败: {e}")
        db.rollback()
    finally:
        db.close()


# ==================== API Endpoints ====================

@router.get("")
async def list_scripts(
    skip: int = 0,
    limit: int = 20,
    script_type: Optional[str] = None,
    tags: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取脚本列表"""
    query = db.query(Script)
    
    # 权限过滤：非管理员只能看到自己创建的、公开的、或有权限的脚本
    if current_user.role != UserRole.SUPER_ADMIN:
        query = query.filter(
            (Script.created_by == current_user.id) |
            (Script.is_public == True) |
            (Script.allowed_roles.contains(current_user.role.value))
        )
    
    # 类型过滤
    if script_type:
        query = query.filter(Script.script_type == script_type)
    
    # 标签过滤
    if tags:
        query = query.filter(Script.tags.contains(tags))
    
    # 搜索
    if search:
        query = query.filter(
            Script.name.contains(search) | 
            Script.description.contains(search)
        )
    
    total = query.count()
    scripts = query.order_by(desc(Script.created_at)).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "items": [{
            "id": s.id,
            "name": s.name,
            "script_type": s.script_type.value,
            "description": s.description,
            "timeout": s.timeout,
            "is_enabled": s.is_enabled,
            "is_public": s.is_public,
            "tags": s.tags,
            "version": s.version,
            "notify_on_success": s.notify_on_success,
            "notify_on_failure": s.notify_on_failure,
            "notify_channels": s.notify_channels,
            "created_by": s.creator.username if s.creator else None,
            "created_at": s.created_at.isoformat() if s.created_at else None
        } for s in scripts]
    }


@router.post("", response_model=MessageResponse)
async def create_script(
    script_data: ScriptCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建脚本"""
    # 检查权限：只有运维和管理员可以创建脚本
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.APPROVAL_ADMIN, UserRole.OPERATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission to create script"
        )
    
    try:
        script_type = ScriptType(script_data.script_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported script type: {script_data.script_type}"
        )
    
    script = Script(
        name=script_data.name,
        script_type=script_type,
        content=script_data.content,
        description=script_data.description,
        params_schema=script_data.params_schema,
        timeout=script_data.timeout,
        max_retries=script_data.max_retries,
        is_public=script_data.is_public,
        allowed_roles=script_data.allowed_roles,
        tags=script_data.tags,
        notify_on_success=script_data.notify_on_success,
        notify_on_failure=script_data.notify_on_failure,
        notify_channels=script_data.notify_channels,
        created_by=current_user.id
    )
    
    db.add(script)
    db.commit()
    db.refresh(script)
    
    return MessageResponse(message=f"脚本创建成功，ID: {script.id}")


@router.get("/{script_id}")
async def get_script(
    script_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取脚本详情"""
    script = db.query(Script).filter(Script.id == script_id).first()
    
    if not script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Script not found"
        )
    
    # 检查权限
    if not check_script_permission(script, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission to access this script"
        )
    
    return {
        "id": script.id,
        "name": script.name,
        "script_type": script.script_type.value,
        "content": script.content,
        "description": script.description,
        "params_schema": script.params_schema,
        "timeout": script.timeout,
        "max_retries": script.max_retries,
        "is_enabled": script.is_enabled,
        "is_public": script.is_public,
        "allowed_roles": script.allowed_roles,
        "tags": script.tags,
        "version": script.version,
        "notify_on_success": script.notify_on_success,
        "notify_on_failure": script.notify_on_failure,
        "notify_channels": script.notify_channels,
        "created_by": script.creator.username if script.creator else None,
        "created_at": script.created_at.isoformat() if script.created_at else None,
        "updated_at": script.updated_at.isoformat() if script.updated_at else None
    }


@router.put("/{script_id}", response_model=MessageResponse)
async def update_script(
    script_id: int,
    script_data: ScriptUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新脚本"""
    script = db.query(Script).filter(Script.id == script_id).first()
    
    if not script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Script not found"
        )
    
    # 只有创建者和管理员可以修改
    if script.created_by != current_user.id and current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission to modify this script"
        )
    
    # 更新字段
    if script_data.name is not None:
        script.name = script_data.name
    if script_data.content is not None:
        script.content = script_data.content
        script.version += 1  # 内容变更时增加版本号
    if script_data.description is not None:
        script.description = script_data.description
    if script_data.params_schema is not None:
        script.params_schema = script_data.params_schema
    if script_data.timeout is not None:
        script.timeout = script_data.timeout
    if script_data.max_retries is not None:
        script.max_retries = script_data.max_retries
    if script_data.is_enabled is not None:
        script.is_enabled = script_data.is_enabled
    if script_data.is_public is not None:
        script.is_public = script_data.is_public
    if script_data.allowed_roles is not None:
        script.allowed_roles = script_data.allowed_roles
    if script_data.tags is not None:
        script.tags = script_data.tags
    # 通知配置更新
    if script_data.notify_on_success is not None:
        script.notify_on_success = script_data.notify_on_success
    if script_data.notify_on_failure is not None:
        script.notify_on_failure = script_data.notify_on_failure
    if script_data.notify_channels is not None:
        script.notify_channels = script_data.notify_channels
    
    db.commit()
    
    return MessageResponse(message="脚本更新成功")


@router.delete("/{script_id}", response_model=MessageResponse)
async def delete_script(
    script_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除脚本"""
    script = db.query(Script).filter(Script.id == script_id).first()
    
    if not script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Script not found"
        )
    
    # 只有创建者和管理员可以删除
    if script.created_by != current_user.id and current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission to delete this script"
        )
    
    db.delete(script)
    db.commit()
    
    return MessageResponse(message="脚本删除成功")


@router.post("/{script_id}/execute")
async def execute_script(
    script_id: int,
    exec_data: ScriptExecute,
    background_tasks: BackgroundTasks,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """执行脚本"""
    script = db.query(Script).filter(Script.id == script_id).first()
    
    if not script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Script not found"
        )
    
    if not script.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Script is disabled"
        )
    
    # 检查权限
    if not check_script_permission(script, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission to execute this script"
        )
    
    # 确定超时时间
    timeout = exec_data.timeout or script.timeout
    
    # 创建执行记录
    execution = ScriptExecution(
        script_id=script.id,
        script_version=script.version,
        trigger_type=TriggerType.MANUAL,
        params=exec_data.params,
        status=ExecutionStatus.PENDING,
        triggered_by=current_user.id,
        trigger_ip=request.client.host if request.client else None
    )
    
    db.add(execution)
    db.commit()
    db.refresh(execution)
    
    if exec_data.async_exec:
        # 异步执行
        background_tasks.add_task(
            execute_script_async,
            execution.id,
            script,
            exec_data.params,
            timeout
        )
        
        return {
            "execution_id": execution.id,
            "status": "pending",
            "message": "脚本已提交执行"
        }
    else:
        # 同步执行
        await execute_script_async(
            execution.id,
            script,
            exec_data.params,
            timeout
        )
        
        db.refresh(execution)
        
        return {
            "execution_id": execution.id,
            "status": execution.status.value,
            "output": execution.output,
            "error_output": execution.error_output,
            "exit_code": execution.exit_code,
            "duration": execution.duration
        }


@router.get("/executions/{execution_id}")
async def get_execution(
    execution_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取执行记录详情"""
    execution = db.query(ScriptExecution).filter(
        ScriptExecution.id == execution_id
    ).first()
    
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution record not found"
        )
    
    return {
        "id": execution.id,
        "script_id": execution.script_id,
        "script_name": execution.script.name if execution.script else None,
        "script_version": execution.script_version,
        "trigger_type": execution.trigger_type.value,
        "params": execution.params,
        "status": execution.status.value,
        "output": execution.output,
        "error_output": execution.error_output,
        "exit_code": execution.exit_code,
        "start_time": execution.start_time.isoformat() if execution.start_time else None,
        "end_time": execution.end_time.isoformat() if execution.end_time else None,
        "duration": execution.duration,
        "triggered_by": execution.trigger_user.username if execution.trigger_user else None,
        "trigger_ip": execution.trigger_ip,
        "retry_count": execution.retry_count,
        "created_at": execution.created_at.isoformat() if execution.created_at else None
    }


@router.get("/executions")
async def list_executions(
    script_id: Optional[int] = None,
    status: Optional[str] = None,
    trigger_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取执行记录列表"""
    query = db.query(ScriptExecution)
    
    if script_id:
        query = query.filter(ScriptExecution.script_id == script_id)
    
    if status:
        try:
            status_enum = ExecutionStatus(status)
            query = query.filter(ScriptExecution.status == status_enum)
        except ValueError:
            pass
    
    if trigger_type:
        try:
            trigger_enum = TriggerType(trigger_type)
            query = query.filter(ScriptExecution.trigger_type == trigger_enum)
        except ValueError:
            pass
    
    # 非管理员只能看到自己触发的执行记录
    if current_user.role != UserRole.SUPER_ADMIN:
        query = query.filter(ScriptExecution.triggered_by == current_user.id)
    
    total = query.count()
    executions = query.order_by(desc(ScriptExecution.created_at)).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "items": [{
            "id": e.id,
            "script_id": e.script_id,
            "script_name": e.script.name if e.script else None,
            "trigger_type": e.trigger_type.value,
            "status": e.status.value,
            "start_time": e.start_time.isoformat() if e.start_time else None,
            "end_time": e.end_time.isoformat() if e.end_time else None,
            "duration": e.duration,
            "triggered_by": e.trigger_user.username if e.trigger_user else None,
            "created_at": e.created_at.isoformat() if e.created_at else None
        } for e in executions]
    }


@router.post("/executions/{execution_id}/cancel", response_model=MessageResponse)
async def cancel_execution(
    execution_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """取消执行中的任务"""
    execution = db.query(ScriptExecution).filter(
        ScriptExecution.id == execution_id
    ).first()
    
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution record not found"
        )
    
    if execution.status != ExecutionStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only cancel running tasks"
        )
    
    # 更新状态
    execution.status = ExecutionStatus.CANCELLED
    execution.end_time = datetime.now()
    if execution.start_time:
        execution.duration = (execution.end_time - execution.start_time).total_seconds()
    execution.error_output = "用户取消执行"
    
    db.commit()
    
    return MessageResponse(message="任务已取消")


@router.post("/{script_id}/duplicate", response_model=MessageResponse)
async def duplicate_script(
    script_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """复制脚本"""
    script = db.query(Script).filter(Script.id == script_id).first()
    
    if not script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Script not found"
        )
    
    # 检查权限
    if not check_script_permission(script, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission to copy this script"
        )
    
    # 创建副本
    new_script = Script(
        name=f"{script.name} (副本)",
        script_type=script.script_type,
        content=script.content,
        description=script.description,
        params_schema=script.params_schema,
        timeout=script.timeout,
        max_retries=script.max_retries,
        is_public=False,  # 副本默认不公开
        allowed_roles=None,
        tags=script.tags,
        created_by=current_user.id
    )
    
    db.add(new_script)
    db.commit()
    
    return MessageResponse(message=f"脚本复制成功，新脚本ID: {new_script.id}")
