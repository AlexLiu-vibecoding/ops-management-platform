"""
变更时间窗口API - 变更时间窗口管理
"""
from datetime import datetime, date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import (
    ChangeWindow, Environment, User
)
from app.schemas import MessageResponse
from app.deps import get_current_user, get_operator

router = APIRouter(prefix="/change-windows", tags=["变更时间窗口"])


# ==================== Schemas ====================

class ChangeWindowCreate(BaseModel):
    """创建变更时间窗口"""
    name: str = Field(..., description="窗口名称")
    description: Optional[str] = Field(None, description="描述")
    window_type: str = Field("allowed", description="窗口类型: forbidden(封禁) 或 allowed(允许)")
    environment_ids: Optional[List[int]] = Field(None, description="应用环境ID列表")
    # 日期范围
    start_date: Optional[str] = Field(None, description="生效开始日期 YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="生效结束日期 YYYY-MM-DD")
    # 时间范围
    start_time: str = Field(..., description="开始时间 HH:MM")
    end_time: str = Field(..., description="结束时间 HH:MM")
    weekdays: Optional[List[int]] = Field(None, description="允许的星期 0-6（0=周一）")
    allow_emergency: bool = Field(False, description="允许紧急变更")
    require_approval: bool = Field(True, description="需要审批")
    min_approvers: int = Field(1, description="最小审批人数")
    auto_reject_outside: bool = Field(False, description="自动拒绝窗口外变更")


class ChangeWindowUpdate(BaseModel):
    """更新变更时间窗口"""
    name: Optional[str] = None
    description: Optional[str] = None
    window_type: Optional[str] = Field(None, description="窗口类型: forbidden(封禁) 或 allowed(允许)")
    environment_ids: Optional[List[int]] = None
    start_date: Optional[str] = Field(None, description="生效开始日期 YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="生效结束日期 YYYY-MM-DD")
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    weekdays: Optional[List[int]] = None
    allow_emergency: Optional[bool] = None
    require_approval: Optional[bool] = None
    min_approvers: Optional[int] = None
    auto_reject_outside: Optional[bool] = None
    is_enabled: Optional[bool] = None


# ==================== APIs ====================

@router.get("", response_model=dict)
async def list_change_windows(
    is_enabled: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取变更时间窗口列表"""
    query = db.query(ChangeWindow)
    
    if is_enabled is not None:
        query = query.filter(ChangeWindow.is_enabled == is_enabled)
    if search:
        query = query.filter(ChangeWindow.name.ilike(f"%{search}%"))
    
    total = query.count()
    items = query.order_by(desc(ChangeWindow.created_at)).offset((page - 1) * limit).limit(limit).all()
    
    # 获取创建人名称
    user_ids = [w.created_by for w in items if w.created_by]
    users = {u.id: u.real_name or u.username for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    
    return {
        "total": total,
        "items": [{
            "id": w.id,
            "name": w.name,
            "description": w.description,
            "window_type": w.window_type or "allowed",
            "environment_ids": w.environment_ids,
            "start_date": w.start_date.isoformat() if w.start_date else None,
            "end_date": w.end_date.isoformat() if w.end_date else None,
            "start_time": w.start_time,
            "end_time": w.end_time,
            "weekdays": w.weekdays,
            "weekdays_label": _get_weekdays_label(w.weekdays),
            "allow_emergency": w.allow_emergency,
            "require_approval": w.require_approval,
            "min_approvers": w.min_approvers,
            "auto_reject_outside": w.auto_reject_outside,
            "is_enabled": w.is_enabled,
            "created_by": w.created_by,
            "created_by_name": users.get(w.created_by),
            "created_at": w.created_at.isoformat() if w.created_at else None
        } for w in items]
    }


@router.post("", response_model=MessageResponse)
async def create_change_window(
    data: ChangeWindowCreate,
    current_user: User = Depends(get_operator),
    db: Session = Depends(get_db)
):
    """创建变更时间窗口"""
    # 验证时间格式
    try:
        datetime.strptime(data.start_time, "%H:%M")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="开始时间格式错误，应为 HH:MM")
    
    try:
        datetime.strptime(data.end_time, "%H:%M")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="结束时间格式错误，应为 HH:MM")
    
    # 验证日期格式
    start_date = None
    end_date = None
    if data.start_date:
        try:
            start_date = datetime.strptime(data.start_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="开始日期格式错误，应为 YYYY-MM-DD")
    if data.end_date:
        try:
            end_date = datetime.strptime(data.end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="结束日期格式错误，应为 YYYY-MM-DD")
    
    # 验证星期
    if data.weekdays:
        for wd in data.weekdays:
            if wd < 0 or wd > 6:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="星期值应在 0-6 之间")
    
    window = ChangeWindow(
        name=data.name,
        description=data.description,
        window_type=data.window_type,
        environment_ids=data.environment_ids,
        start_date=start_date,
        end_date=end_date,
        start_time=data.start_time,
        end_time=data.end_time,
        weekdays=data.weekdays,
        allow_emergency=data.allow_emergency,
        require_approval=data.require_approval,
        min_approvers=data.min_approvers,
        auto_reject_outside=data.auto_reject_outside,
        created_by=current_user.id
    )
    
    db.add(window)
    db.commit()
    
    return MessageResponse(message="创建成功")


@router.get("/{window_id}", response_model=dict)
async def get_change_window(
    window_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取变更时间窗口详情"""
    window = db.query(ChangeWindow).filter(ChangeWindow.id == window_id).first()
    if not window:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="时间窗口不存在")
    
    created_by_name = None
    if window.created_by:
        user = db.query(User).filter(User.id == window.created_by).first()
        created_by_name = user.real_name or user.username if user else None
    
    # 获取环境名称
    environment_names = []
    if window.environment_ids:
        environments = db.query(Environment).filter(Environment.id.in_(window.environment_ids)).all()
        environment_names = [{"id": e.id, "name": e.name} for e in environments]
    
    return {
        "id": window.id,
        "name": window.name,
        "description": window.description,
        "environment_ids": window.environment_ids,
        "environment_names": environment_names,
        "start_date": window.start_date.isoformat() if window.start_date else None,
        "end_date": window.end_date.isoformat() if window.end_date else None,
        "start_time": window.start_time,
        "end_time": window.end_time,
        "weekdays": window.weekdays,
        "weekdays_label": _get_weekdays_label(window.weekdays),
        "allow_emergency": window.allow_emergency,
        "require_approval": window.require_approval,
        "min_approvers": window.min_approvers,
        "auto_reject_outside": window.auto_reject_outside,
        "is_enabled": window.is_enabled,
        "created_by": window.created_by,
        "created_by_name": created_by_name,
        "created_at": window.created_at.isoformat() if window.created_at else None,
        "updated_at": window.updated_at.isoformat() if window.updated_at else None
    }


@router.put("/{window_id}", response_model=MessageResponse)
async def update_change_window(
    window_id: int,
    data: ChangeWindowUpdate,
    current_user: User = Depends(get_operator),
    db: Session = Depends(get_db)
):
    """更新变更时间窗口"""
    window = db.query(ChangeWindow).filter(ChangeWindow.id == window_id).first()
    if not window:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="时间窗口不存在")
    
    if data.name is not None:
        window.name = data.name
    if data.description is not None:
        window.description = data.description
    if data.window_type is not None:
        if data.window_type not in ["forbidden", "allowed"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="窗口类型必须为 forbidden 或 allowed")
        window.window_type = data.window_type
    if data.environment_ids is not None:
        window.environment_ids = data.environment_ids
    if data.start_date is not None:
        try:
            window.start_date = datetime.strptime(data.start_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="开始日期格式错误，应为 YYYY-MM-DD")
    if data.end_date is not None:
        try:
            window.end_date = datetime.strptime(data.end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="结束日期格式错误，应为 YYYY-MM-DD")
    if data.start_time is not None:
        try:
            datetime.strptime(data.start_time, "%H:%M")
            window.start_time = data.start_time
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="开始时间格式错误，应为 HH:MM")
    if data.end_time is not None:
        try:
            datetime.strptime(data.end_time, "%H:%M")
            window.end_time = data.end_time
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="结束时间格式错误，应为 HH:MM")
    if data.weekdays is not None:
        for wd in data.weekdays:
            if wd < 0 or wd > 6:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="星期值应在 0-6 之间")
        window.weekdays = data.weekdays
    if data.allow_emergency is not None:
        window.allow_emergency = data.allow_emergency
    if data.require_approval is not None:
        window.require_approval = data.require_approval
    if data.min_approvers is not None:
        window.min_approvers = data.min_approvers
    if data.auto_reject_outside is not None:
        window.auto_reject_outside = data.auto_reject_outside
    if data.is_enabled is not None:
        window.is_enabled = data.is_enabled
    
    db.commit()
    return MessageResponse(message="更新成功")


@router.delete("/{window_id}", response_model=MessageResponse)
async def delete_change_window(
    window_id: int,
    current_user: User = Depends(get_operator),
    db: Session = Depends(get_db)
):
    """删除变更时间窗口"""
    window = db.query(ChangeWindow).filter(ChangeWindow.id == window_id).first()
    if not window:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="时间窗口不存在")
    
    db.delete(window)
    db.commit()
    return MessageResponse(message="删除成功")


@router.post("/{window_id}/toggle", response_model=MessageResponse)
async def toggle_change_window(
    window_id: int,
    current_user: User = Depends(get_operator),
    db: Session = Depends(get_db)
):
    """启用/禁用变更时间窗口"""
    window = db.query(ChangeWindow).filter(ChangeWindow.id == window_id).first()
    if not window:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="时间窗口不存在")
    
    window.is_enabled = not window.is_enabled
    db.commit()
    
    return MessageResponse(message=f"时间窗口已{'禁用' if not window.is_enabled else '启用'}")


@router.post("/check", response_model=dict)
async def check_change_window(
    environment_id: int,
    check_time: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """检查指定时间是否在变更窗口内"""
    # 解析检查时间
    if check_time:
        try:
            dt = datetime.fromisoformat(check_time)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="时间格式错误")
    else:
        dt = datetime.now()
    
    # 查找该环境的变更窗口
    windows = db.query(ChangeWindow).filter(
        ChangeWindow.is_enabled == True
    ).all()
    
    # 过滤出适用于该环境的窗口
    applicable_windows = []
    for w in windows:
        if w.environment_ids is None or len(w.environment_ids) == 0:
            applicable_windows.append(w)
        elif environment_id in (w.environment_ids or []):
            applicable_windows.append(w)
    
    if not applicable_windows:
        return {
            "can_change": True,
            "message": "未配置变更窗口，允许变更",
            "windows": []
        }
    
    result_windows = []
    # 默认允许变更
    can_change = True
    # 是否在封禁窗口内
    in_forbidden = False
    # 是否在允许窗口内（当存在允许窗口时，默认变为不允许）
    has_allow_window = False
    in_allow_window = False
    
    for window in applicable_windows:
        window_check = _check_single_window(window, dt)
        result_windows.append(window_check)
        
        # 根据窗口类型处理
        if window.window_type == "forbidden":
            # 封禁窗口：在窗口内则禁止变更
            if window_check["in_window"]:
                in_forbidden = True
        else:
            # 允许窗口：存在允许窗口时，默认不允许，只有在窗口内才允许
            has_allow_window = True
            if window_check["in_window"]:
                in_allow_window = True
    
    # 最终判断：
    # 1. 如果在封禁窗口内，禁止变更
    # 2. 如果存在允许窗口，只有在允许窗口内才能变更
    # 3. 否则默认允许
    if in_forbidden:
        can_change = False
    elif has_allow_window:
        can_change = in_allow_window
    else:
        can_change = True
    
    # 检查是否有允许紧急变更的窗口
    allow_emergency = any(w.get("allow_emergency") for w in result_windows)
    
    # 生成消息
    if can_change:
        message = "可以提交变更"
    else:
        if in_forbidden:
            message = "当前在封禁窗口内，禁止变更"
        else:
            message = "当前不在允许窗口内，禁止变更"
        if allow_emergency:
            message += "，可提交紧急变更"
    
    return {
        "can_change": can_change,
        "message": message,
        "allow_emergency": allow_emergency and not can_change,
        "in_forbidden": in_forbidden,
        "windows": result_windows
    }


def _check_single_window(window: ChangeWindow, dt: datetime) -> dict:
    """检查单个窗口"""
    result = {
        "id": window.id,
        "name": window.name,
        "window_type": window.window_type or "allowed",
        "allow_emergency": window.allow_emergency,
        "in_window": False,
        "reason": ""
    }
    
    # 如果没有配置时间限制，则全天生效
    time_matched = True
    if window.start_time and window.end_time:
        check_time_str = dt.strftime("%H:%M")
        # 将时间对象转换为字符串格式
        start_time = window.start_time.strftime("%H:%M") if hasattr(window.start_time, 'strftime') else str(window.start_time)
        end_time = window.end_time.strftime("%H:%M") if hasattr(window.end_time, 'strftime') else str(window.end_time)
        
        if start_time <= end_time:
            # 不跨天
            time_matched = start_time <= check_time_str <= end_time
        else:
            # 跨天 (如 22:00 - 02:00)
            time_matched = check_time_str >= start_time or check_time_str <= end_time
        
        if not time_matched:
            result["reason"] = f"当前时间不在 {start_time}-{end_time} 范围内"
            return result
    
    # 检查日期范围
    date_matched = True
    if window.start_date and window.end_date:
        check_date = dt.date()
        if not (window.start_date <= check_date <= window.end_date):
            date_matched = False
            result["reason"] = f"不在日期范围内 ({window.start_date} ~ {window.end_date})"
            return result
    
    # 检查星期
    weekday_matched = True
    if window.weekdays:
        weekday = dt.weekday()  # 0-6, Monday=0
        if weekday not in window.weekdays:
            weekday_matched = False
            result["reason"] = f"星期{['一', '二', '三', '四', '五', '六', '日'][weekday]}不在允许范围内"
            return result
    
    # 所有条件都满足，则在窗口内
    result["in_window"] = True
    window_type_name = "封禁" if window.window_type == "forbidden" else "允许"
    result["reason"] = f"在{window_type_name}窗口内"
    
    return result


def _get_weekdays_label(weekdays: Optional[List[int]]) -> str:
    """获取星期标签"""
    if not weekdays:
        return "每天"
    
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    selected = [weekday_names[i] for i in sorted(weekdays)]
    
    # 简化显示
    if weekdays == [0, 1, 2, 3, 4]:
        return "工作日"
    elif weekdays == [5, 6]:
        return "周末"
    else:
        return ", ".join(selected)
