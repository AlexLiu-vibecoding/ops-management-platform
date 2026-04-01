"""通知模板管理 API"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import NotificationTemplate


router = APIRouter(prefix="/notification-templates", tags=["通知模板"])


# ==================== Schemas ====================

class BaseResponse(BaseModel):
    """基础响应"""
    code: int = 0
    message: str = "success"


class NotificationTemplateCreate(BaseModel):
    """创建通知模板请求"""
    name: str = Field(..., min_length=1, max_length=100, description="模板名称")
    description: Optional[str] = Field(None, max_length=200, description="模板描述")
    notification_type: str = Field(..., description="通知类型: approval/alert/scheduled_task")
    sub_type: Optional[str] = Field(None, description="细分类型")
    title_template: str = Field(..., min_length=1, max_length=200, description="标题模板")
    content_template: str = Field(..., min_length=1, description="内容模板(Markdown)")
    variables: Optional[List[Dict[str, Any]]] = Field(None, description="可用变量列表")
    is_enabled: bool = Field(True, description="是否启用")
    is_default: bool = Field(False, description="是否默认模板")


class NotificationTemplateUpdate(BaseModel):
    """更新通知模板请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="模板名称")
    description: Optional[str] = Field(None, max_length=200, description="模板描述")
    notification_type: Optional[str] = Field(None, description="通知类型")
    sub_type: Optional[str] = Field(None, description="细分类型")
    title_template: Optional[str] = Field(None, min_length=1, max_length=200, description="标题模板")
    content_template: Optional[str] = Field(None, min_length=1, description="内容模板")
    variables: Optional[List[Dict[str, Any]]] = Field(None, description="可用变量列表")
    is_enabled: Optional[bool] = Field(None, description="是否启用")
    is_default: Optional[bool] = Field(None, description="是否默认模板")


class NotificationTemplateResponse(BaseModel):
    """通知模板响应"""
    id: int
    name: str
    description: Optional[str]
    notification_type: str
    sub_type: Optional[str]
    title_template: str
    content_template: str
    variables: Optional[List[Dict[str, Any]]]
    is_enabled: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginationData(BaseModel):
    """分页数据"""
    items: List[Any]
    total: int
    page: int
    page_size: int


class NotificationTemplateListResponse(BaseResponse):
    data: PaginationData


class NotificationTemplateDetailResponse(BaseResponse):
    data: Optional[NotificationTemplateResponse] = None


# ==================== APIs ====================

@router.get("", response_model=NotificationTemplateListResponse)
async def list_notification_templates(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    notification_type: Optional[str] = Query(None, description="通知类型"),
    is_enabled: Optional[bool] = Query(None, description="是否启用"),
    db: Session = Depends(get_db)
):
    """获取通知模板列表"""
    
    query = db.query(NotificationTemplate)
    
    if notification_type:
        query = query.filter(NotificationTemplate.notification_type == notification_type)
    if is_enabled is not None:
        query = query.filter(NotificationTemplate.is_enabled == is_enabled)
    
    total = query.count()
    templates = query.order_by(desc(NotificationTemplate.created_at)) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()
    
    return NotificationTemplateListResponse(
        code=0,
        message="获取成功",
        data=PaginationData(
            items=[NotificationTemplateResponse.model_validate(t) for t in templates],
            total=total,
            page=page,
            page_size=page_size
        )
    )


@router.get("/{template_id}", response_model=NotificationTemplateDetailResponse)
async def get_notification_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """获取通知模板详情"""
    
    template = db.query(NotificationTemplate).filter(NotificationTemplate.id == template_id).first()
    
    if not template:
        return NotificationTemplateDetailResponse(
            code=404,
            message="模板不存在"
        )
    
    return NotificationTemplateDetailResponse(
        code=0,
        message="获取成功",
        data=NotificationTemplateResponse.model_validate(template)
    )


@router.post("", response_model=NotificationTemplateDetailResponse)
async def create_notification_template(
    data: NotificationTemplateCreate,
    db: Session = Depends(get_db)
):
    """创建通知模板"""
    
    # 检查名称是否已存在
    existing = db.query(NotificationTemplate).filter(NotificationTemplate.name == data.name).first()
    if existing:
        return NotificationTemplateDetailResponse(
            code=400,
            message="模板名称已存在"
        )
    
    # 如果设置为默认，取消其他模板的默认状态
    if data.is_default:
        db.query(NotificationTemplate).filter(
            NotificationTemplate.notification_type == data.notification_type,
            NotificationTemplate.is_default == True
        ).update({"is_default": False})
    
    # 如果没有提供变量，使用默认变量
    if data.variables is None:
        data.variables = get_default_variables(data.notification_type)
    
    template = NotificationTemplate(**data.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return NotificationTemplateDetailResponse(
        code=0,
        message="创建成功",
        data=NotificationTemplateResponse.model_validate(template)
    )


@router.put("/{template_id}", response_model=NotificationTemplateDetailResponse)
async def update_notification_template(
    template_id: int,
    data: NotificationTemplateUpdate,
    db: Session = Depends(get_db)
):
    """更新通知模板"""
    
    template = db.query(NotificationTemplate).filter(NotificationTemplate.id == template_id).first()
    
    if not template:
        return NotificationTemplateDetailResponse(
            code=404,
            message="模板不存在"
        )
    
    # 检查名称是否冲突
    if data.name and data.name != template.name:
        existing = db.query(NotificationTemplate).filter(NotificationTemplate.name == data.name).first()
        if existing:
            return NotificationTemplateDetailResponse(
                code=400,
                message="模板名称已存在"
            )
    
    # 如果设置为默认，取消其他模板的默认状态
    if data.is_default:
        new_type = data.notification_type or template.notification_type
        db.query(NotificationTemplate).filter(
            NotificationTemplate.notification_type == new_type,
            NotificationTemplate.id != template_id,
            NotificationTemplate.is_default == True
        ).update({"is_default": False})
    
    # 更新字段
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(template, field, value)
    
    db.commit()
    db.refresh(template)
    
    return NotificationTemplateDetailResponse(
        code=0,
        message="更新成功",
        data=NotificationTemplateResponse.model_validate(template)
    )


@router.delete("/{template_id}", response_model=BaseResponse)
async def delete_notification_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """删除通知模板"""
    
    template = db.query(NotificationTemplate).filter(NotificationTemplate.id == template_id).first()
    
    if not template:
        return BaseResponse(code=404, message="模板不存在")
    
    db.delete(template)
    db.commit()
    
    return BaseResponse(code=0, message="删除成功")


@router.get("/default/{notification_type}", response_model=NotificationTemplateDetailResponse)
async def get_default_template_endpoint(
    notification_type: str,
    sub_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取指定类型的默认模板"""
    
    # 先查找数据库中的默认模板
    query = db.query(NotificationTemplate).filter(
        NotificationTemplate.notification_type == notification_type,
        NotificationTemplate.is_enabled == True,
        NotificationTemplate.is_default == True
    )
    
    if sub_type:
        query = query.filter(NotificationTemplate.sub_type == sub_type)
    
    template = query.first()
    
    if template:
        return NotificationTemplateDetailResponse(
            code=0,
            message="获取成功",
            data=NotificationTemplateResponse.model_validate(template)
        )
    
    # 如果没有找到，返回系统默认模板
    default_content = {
        "approval": {
            "title": "变更审批通知",
            "content": """## 变更审批通知

**申请信息**
- 标题: {title}
- 申请人: {requester_name}
- 提交时间: {created_at}

**变更详情**
- 目标实例: {instance_name}
- 变更类型: {change_type}
- 风险等级: {risk_level}

[点击通过]({approve_url}) | [点击拒绝]({reject_url})"""
        },
        "alert": {
            "title": "告警通知: {alert_title}",
            "content": """## 告警通知

**告警详情**
- 告警标题: {alert_title}
- 告警级别: {alert_level}
- 目标实例: {instance_name}
- 指标: {metric_name}
- 当前值: {current_value}
- 阈值: {threshold}"""
        },
        "scheduled_task": {
            "title": "定时任务执行通知: {task_name}",
            "content": """## 定时任务执行通知

**任务信息**
- 任务名称: {task_name}
- 执行脚本: {script_name}

**执行详情**
- 状态: {status}
- 耗时: {duration}
- 退出码: {exit_code}
- 开始时间: {start_time}
- 结束时间: {end_time}"""
        }
    }
    
    default_vars = {
        "approval": [
            {"name": "title", "description": "审批标题", "example": "数据库结构变更"},
            {"name": "requester_name", "description": "申请人姓名", "example": "张三"},
            {"name": "instance_name", "description": "实例名称", "example": "生产数据库"},
            {"name": "change_type", "description": "变更类型", "example": "DDL"},
            {"name": "risk_level", "description": "风险等级", "example": "高风险"},
            {"name": "approve_url", "description": "审批通过链接", "example": "https://..."},
            {"name": "reject_url", "description": "审批拒绝链接", "example": "https://..."}
        ],
        "alert": [
            {"name": "alert_title", "description": "告警标题", "example": "慢查询告警"},
            {"name": "instance_name", "description": "实例名称", "example": "生产数据库"},
            {"name": "alert_level", "description": "告警级别", "example": "critical"},
            {"name": "metric_name", "description": "指标名称", "example": "CPU使用率"},
            {"name": "current_value", "description": "当前值", "example": "85%"},
            {"name": "threshold", "description": "阈值", "example": "80%"}
        ],
        "scheduled_task": [
            {"name": "task_name", "description": "任务名称", "example": "每日备份"},
            {"name": "script_name", "description": "脚本名称", "example": "backup.sh"},
            {"name": "status", "description": "执行状态", "example": "成功"},
            {"name": "duration", "description": "执行耗时", "example": "60.5秒"},
            {"name": "exit_code", "description": "退出码", "example": "0"},
            {"name": "start_time", "description": "开始时间", "example": "2024-01-01 00:00:00"},
            {"name": "end_time", "description": "结束时间", "example": "2024-01-01 00:01:00"}
        ]
    }
    
    content = default_content.get(notification_type, {"title": "通知", "content": "通知内容"})
    variables = default_vars.get(notification_type, [])
    
    return NotificationTemplateDetailResponse(
        code=0,
        message="获取成功（系统默认）",
        data=NotificationTemplateResponse(
            id=0,
            name=f"系统默认-{notification_type}",
            description="系统内置默认模板",
            notification_type=notification_type,
            sub_type=sub_type,
            title_template=content["title"],
            content_template=content["content"],
            variables=variables,
            is_enabled=True,
            is_default=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    )
