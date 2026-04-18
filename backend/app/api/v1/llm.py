"""
LLM管理API
用于监控和控制LLM负载均衡器
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from app.core.llm_balancer import get_llm_balancer, LLMBalancer
from app.services.llm_service import LLMService
from app.api.v1.auth import get_current_user
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class SwitchModelRequest(BaseModel):
    """切换模型请求"""
    target_model: str = Field(..., description="目标模型名称")


class TestModelRequest(BaseModel):
    """测试模型请求"""
    model: str = Field(..., description="模型名称")


@router.get("/status", response_model=dict)
async def get_balancer_status(
    current_user: User = Depends(get_current_user)
):
    """
    获取负载均衡器状态

    返回当前使用的模型、失败次数等信息
    """
    try:
        balancer = await get_llm_balancer()
        status = await balancer.get_status()

        return {
            "code": 200,
            "message": "success",
            "data": status
        }

    except Exception as e:
        logger.error(f"获取负载均衡器状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/switch", response_model=dict)
async def switch_model(
    request: SwitchModelRequest,
    current_user: User = Depends(get_current_user)
):
    """
    手动切换模型

    允许管理员手动切换到指定模型
    """
    try:
        balancer = await get_llm_balancer()
        await balancer.manual_switch(request.target_model)

        return {
            "code": 200,
            "message": f"已切换到模型: {request.target_model}",
            "data": {
                "current_model": request.target_model
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"切换模型失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test", response_model=dict)
async def test_model(
    request: TestModelRequest,
    current_user: User = Depends(get_current_user)
):
    """
    测试模型可用性

    发送测试请求检查模型是否正常工作
    """
    try:
        llm_service = LLMService()
        is_available = await llm_service.test_model(request.model)

        return {
            "code": 200,
            "message": "success",
            "data": {
                "model": request.model,
                "available": is_available
            }
        }

    except Exception as e:
        logger.error(f"测试模型失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset", response_model=dict)
async def reset_failures(
    current_user: User = Depends(get_current_user)
):
    """
    重置失败计数

    清除所有模型的失败计数
    """
    try:
        balancer = await get_llm_balancer()

        # 重置失败计数
        if balancer.redis_client:
            await balancer.redis_client.set(balancer.REDIS_KEY_PRIMARY_FAILURES, 0)
            await balancer.redis_client.set(balancer.REDIS_KEY_BACKUP_FAILURES, 0)

        return {
            "code": 200,
            "message": "失败计数已重置",
            "data": None
        }

    except Exception as e:
        logger.error(f"重置失败计数失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
