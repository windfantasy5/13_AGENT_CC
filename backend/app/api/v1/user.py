"""
用户管理API
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import get_db, get_redis
from app.schemas.user import UserResponse, UserUpdate, PasswordUpdate
from app.schemas.response import ResponseModel, success_response, error_response
from app.models.user import User
from app.core.security import verify_password, get_password_hash
from app.api.deps import get_current_user
import json

router = APIRouter()


@router.get("/me", response_model=ResponseModel)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    redis = Depends(get_redis)
):
    """获取当前用户信息"""
    # 尝试从Redis获取
    cached = await redis.get(f"user:info:{current_user.id}")
    if cached:
        user_info = json.loads(cached)
    else:
        user_info = UserResponse.from_orm(current_user).dict()
        await redis.setex(
            f"user:info:{current_user.id}",
            3600,
            json.dumps(user_info, ensure_ascii=False, default=str)
        )

    return success_response(data=user_info)


@router.put("/me", response_model=ResponseModel)
async def update_user_info(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
):
    """更新用户信息"""
    # 更新字段
    if user_data.nickname is not None:
        current_user.nickname = user_data.nickname
    if user_data.avatar is not None:
        current_user.avatar = user_data.avatar
    if user_data.hobbies is not None:
        current_user.hobbies = user_data.hobbies
    if user_data.gender is not None:
        current_user.gender = user_data.gender
    if user_data.phone is not None:
        current_user.phone = user_data.phone
    if user_data.description is not None:
        current_user.description = user_data.description

    await db.commit()
    await db.refresh(current_user)

    # 清除Redis缓存
    await redis.delete(f"user:info:{current_user.id}")

    return success_response(
        data=UserResponse.from_orm(current_user).dict(),
        message="更新成功"
    )


@router.put("/me/password", response_model=ResponseModel)
async def update_password(
    password_data: PasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """修改密码"""
    # 验证旧密码
    if not verify_password(password_data.old_password, current_user.password_hash):
        return error_response(code=400, message="旧密码错误")

    # 更新密码
    current_user.password_hash = get_password_hash(password_data.new_password)
    await db.commit()

    return success_response(message="密码修改成功")
