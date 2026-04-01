"""
认证相关API
"""
import random
import string
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, LoginLog, UserRegistrationRequest, RegistrationStatus, UserRole
from app.schemas import (
    UserLogin, UserCreate, UserUpdate, UserResponse, TokenResponse,
    UserRegister, RegistrationAction, RegistrationResponse
)
from app.utils.auth import (
    hash_password, verify_password, create_access_token
)
from app.deps import get_current_user, get_super_admin
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
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """获取当前用户信息"""
    return UserResponse.model_validate(current_user)


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


# ============ 注册相关API ============

@router.post("/register", response_model=RegistrationResponse)
async def register(
    register_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    用户注册申请
    
    - 检查用户名是否已存在
    - 检查是否有待审批的注册申请
    - 创建注册申请记录
    """
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == register_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # 检查是否有待审批的注册申请
    existing_request = db.query(UserRegistrationRequest).filter(
        UserRegistrationRequest.username == register_data.username,
        UserRegistrationRequest.status == RegistrationStatus.PENDING
    ).first()
    if existing_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已有待审批的注册申请，请等待管理员审核"
        )
    
    # 创建注册申请
    registration = UserRegistrationRequest(
        username=register_data.username,
        password_hash=hash_password(register_data.password),
        real_name=register_data.real_name,
        email=register_data.email,
        phone=register_data.phone,
        reason=register_data.reason,
        status=RegistrationStatus.PENDING
    )
    db.add(registration)
    db.commit()
    db.refresh(registration)
    
    return RegistrationResponse(
        id=registration.id,
        username=registration.username,
        real_name=registration.real_name,
        email=registration.email,
        phone=registration.phone,
        reason=registration.reason,
        status=registration.status,
        reviewer_id=registration.reviewer_id,
        reviewer_name=None,
        review_time=registration.review_time,
        review_comment=registration.review_comment,
        created_at=registration.created_at
    )


@router.get("/register/status/{username}", response_model=RegistrationResponse)
async def check_registration_status(
    username: str,
    db: Session = Depends(get_db)
):
    """查询注册申请状态"""
    registration = db.query(UserRegistrationRequest).filter(
        UserRegistrationRequest.username == username
    ).order_by(UserRegistrationRequest.created_at.desc()).first()
    
    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到注册申请记录"
        )
    
    return RegistrationResponse(
        id=registration.id,
        username=registration.username,
        real_name=registration.real_name,
        email=registration.email,
        phone=registration.phone,
        reason=registration.reason,
        status=registration.status,
        reviewer_id=registration.reviewer_id,
        reviewer_name=registration.reviewer.real_name if registration.reviewer else None,
        review_time=registration.review_time,
        review_comment=registration.review_comment,
        created_at=registration.created_at
    )


@router.get("/registrations", response_model=list[RegistrationResponse])
async def list_registrations(
    status_filter: RegistrationStatus = None,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """
    获取注册申请列表（仅超级管理员）
    """
    query = db.query(UserRegistrationRequest)
    
    if status_filter:
        query = query.filter(UserRegistrationRequest.status == status_filter)
    
    registrations = query.order_by(UserRegistrationRequest.created_at.desc()).all()
    
    return [
        RegistrationResponse(
            id=r.id,
            username=r.username,
            real_name=r.real_name,
            email=r.email,
            phone=r.phone,
            reason=r.reason,
            status=r.status,
            reviewer_id=r.reviewer_id,
            reviewer_name=r.reviewer.real_name if r.reviewer else None,
            review_time=r.review_time,
            review_comment=r.review_comment,
            created_at=r.created_at
        )
        for r in registrations
    ]


@router.post("/registrations/{registration_id}/review", response_model=RegistrationResponse)
async def review_registration(
    registration_id: int,
    action_data: RegistrationAction,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """
    审批注册申请（仅超级管理员）
    """
    registration = db.query(UserRegistrationRequest).filter(
        UserRegistrationRequest.id == registration_id
    ).first()
    
    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="注册申请不存在"
        )
    
    if registration.status != RegistrationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该申请已被处理"
        )
    
    # 更新申请状态
    registration.status = RegistrationStatus.APPROVED if action_data.approved else RegistrationStatus.REJECTED
    registration.reviewer_id = current_user.id
    registration.review_time = datetime.now()
    registration.review_comment = action_data.comment
    
    # 如果通过，创建用户
    if action_data.approved:
        # 再次检查用户名是否已被占用
        existing_user = db.query(User).filter(User.username == registration.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已被占用"
            )
        
        # 创建用户
        new_user = User(
            username=registration.username,
            password_hash=registration.password_hash,
            real_name=registration.real_name,
            email=registration.email,
            phone=registration.phone,
            role=UserRole.READONLY,
            status=True
        )
        db.add(new_user)
    
    db.commit()
    db.refresh(registration)
    
    return RegistrationResponse(
        id=registration.id,
        username=registration.username,
        real_name=registration.real_name,
        email=registration.email,
        phone=registration.phone,
        reason=registration.reason,
        status=registration.status,
        reviewer_id=registration.reviewer_id,
        reviewer_name=registration.reviewer.real_name if registration.reviewer else None,
        review_time=registration.review_time,
        review_comment=registration.review_comment,
        created_at=registration.created_at
    )
