"""
认证API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from app.config.database import get_db, get_redis
from app.schemas.user import UserRegister, UserLogin, TokenResponse, UserResponse
from app.schemas.response import ResponseModel, success_response, error_response
from app.models.user import User, UserToken, Role, UserRole
from app.core.security import verify_password, get_password_hash, create_access_token
from app.config.settings import settings
from app.api.deps import get_current_user, get_client_ip
import json

router = APIRouter()


@router.post("/register", response_model=ResponseModel)
async def register(
    user_data: UserRegister,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """用户注册"""
    # 检查用户名是否存在
    result = await db.execute(select(User).where(User.username == user_data.username))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        return error_response(code=400, message="用户名已存在")

    # 创建用户
    user = User(
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        nickname=user_data.nickname or user_data.username,
        phone=user_data.phone
    )
    db.add(user)
    await db.flush()

    # 分配默认角色(普通用户)
    role_result = await db.execute(select(Role).where(Role.name == "普通用户"))
    default_role = role_result.scalar_one_or_none()

    if default_role:
        user_role = UserRole(user_id=user.id, role_id=default_role.id)
        db.add(user_role)

    await db.commit()
    await db.refresh(user)

    # 记录日志
    from app.models.conversation import SystemLog
    log = SystemLog(
        user_id=user.id,
        action="register",
        module="auth",
        details=f"用户注册: {user.username}",
        ip_address=get_client_ip(request)
    )
    db.add(log)
    await db.commit()

    return success_response(
        data={"user_id": user.id, "username": user.username},
        message="注册成功"
    )


@router.post("/login", response_model=ResponseModel)
async def login(
    user_data: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
):
    """用户登录"""
    # 查询用户
    result = await db.execute(select(User).where(User.username == user_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(user_data.password, user.password_hash):
        return error_response(code=401, message="用户名或密码错误")

    if not user.is_active:
        return error_response(code=403, message="用户已被禁用")

    # 创建token
    expires_delta = timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
    access_token = create_access_token(
        data={"user_id": user.id, "username": user.username},
        expires_delta=expires_delta
    )

    # 保存token到数据库
    expires_at = datetime.utcnow() + expires_delta
    user_token = UserToken(
        user_id=user.id,
        token=access_token,
        expires_at=expires_at
    )
    db.add(user_token)

    # 缓存用户信息到Redis
    user_info = {
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "avatar": user.avatar
    }
    await redis.setex(
        f"user:token:{user.id}",
        settings.ACCESS_TOKEN_EXPIRE_DAYS * 86400,
        access_token
    )
    await redis.setex(
        f"user:info:{user.id}",
        3600,
        json.dumps(user_info, ensure_ascii=False)
    )

    # 记录日志
    from app.models.conversation import SystemLog
    log = SystemLog(
        user_id=user.id,
        action="login",
        module="auth",
        details=f"用户登录: {user.username}",
        ip_address=get_client_ip(request)
    )
    db.add(log)
    await db.commit()

    # 构造响应
    token_response = TokenResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_DAYS * 86400,
        user=UserResponse.from_orm(user)
    )

    return success_response(data=token_response.dict(), message="登录成功")


@router.post("/logout", response_model=ResponseModel)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
):
    """用户登出"""
    # 删除Redis缓存
    await redis.delete(f"user:token:{current_user.id}")
    await redis.delete(f"user:info:{current_user.id}")

    # 记录日志
    from app.models.conversation import SystemLog
    log = SystemLog(
        user_id=current_user.id,
        action="logout",
        module="auth",
        details=f"用户登出: {current_user.username}",
        ip_address=get_client_ip(request)
    )
    db.add(log)
    await db.commit()

    return success_response(message="登出成功")


@router.get("/verify", response_model=ResponseModel)
async def verify_token(current_user: User = Depends(get_current_user)):
    """验证Token"""
    return success_response(
        data=UserResponse.from_orm(current_user).dict(),
        message="Token有效"
    )
