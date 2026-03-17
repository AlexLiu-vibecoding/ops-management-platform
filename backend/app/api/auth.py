"""
认证相关API
"""
import random
import string
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, LoginLog
from app.schemas import UserLogin, UserCreate, UserUpdate, UserResponse, TokenResponse
from app.utils.auth import (
    hash_password, verify_password, create_access_token
)
from app.deps import get_current_user
from app.config import settings
import httpx

router = APIRouter(prefix="/auth", tags=["认证"])


def generate_captcha() -> str:
    """生成验证码"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))


def check_login_attempts(db: Session, user: User) -> bool:
    """检查登录失败次数"""
    if user.locked_until and user.locked_until > datetime.now():
        return False
    if user.failed_login_count >= 5:
        # 锁定30分钟
        user.locked_until = datetime.now() + timedelta(minutes=30)
        db.commit()
        return False
    return True


def record_login_attempt(db: Session, user: User, request: Request, success: bool, reason: str = None):
    """记录登录尝试"""
    # 更新用户登录信息
    if success:
        user.failed_login_count = 0
        user.locked_until = None
        user.last_login_time = datetime.now()
        user.last_login_ip = request.client.host
    else:
        user.failed_login_count = (user.failed_login_count or 0) + 1
    
    db.commit()
    
    # 记录登录日志
    login_log = LoginLog(
        user_id=user.id,
        username=user.username,
        login_ip=request.client.host,
        login_device=request.headers.get("user-agent", ""),
        login_status="success" if success else "failed",
        failure_reason=reason
    )
    db.add(login_log)
    db.commit()


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    user_login: UserLogin,
    db: Session = Depends(get_db)
):
    """
    用户登录
    
    - 验证用户名密码
    - 检查登录失败次数
    - 生成JWT Token
    """
    # 查找用户
    user = db.query(User).filter(User.username == user_login.username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    # 检查账户状态
    if not user.status:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用"
        )
    
    # 检查登录尝试
    if not check_login_attempts(db, user):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="登录失败次数过多，账户已锁定30分钟"
        )
    
    # 验证密码
    if not verify_password(user_login.password, user.password_hash):
        record_login_attempt(db, user, request, False, "密码错误")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    # 登录成功
    record_login_attempt(db, user, request, True)
    
    # 生成Token
    access_token = create_access_token(
        data={"sub": user.id, "username": user.username, "role": user.role.value}
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_HOURS * 3600,
        user=UserResponse.from_orm(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """获取当前用户信息"""
    return UserResponse.from_orm(current_user)


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user)
):
    """用户登出（客户端清除Token即可）"""
    return {"message": "登出成功"}


@router.put("/password")
async def change_password(
    old_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """修改密码"""
    # 验证旧密码
    if not verify_password(old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码错误"
        )
    
    # 更新密码
    current_user.password_hash = hash_password(new_password)
    db.commit()
    
    return {"message": "密码修改成功"}
