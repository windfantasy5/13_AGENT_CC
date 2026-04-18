"""
LLM负载均衡器
实现主备模式、熔断机制和健康检查
"""
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import redis.asyncio as aioredis
from app.config.settings import settings

logger = logging.getLogger(__name__)


class LLMBalancer:
    """LLM负载均衡器"""

    # 模型配置
    PRIMARY_MODEL = "qwen3-max"  # 主模型（网络API）
    BACKUP_MODEL = "deepseek-r1:7b"  # 备用模型（ollama本地）

    # 熔断配置
    MAX_FAILURES = 5  # 最大连续失败次数
    HEALTH_CHECK_INTERVAL = 60  # 健康检查间隔（秒）
    FAILURE_RESET_TIME = 300  # 失败计数重置时间（秒）

    # Redis键名
    REDIS_KEY_CURRENT_MODEL = "llm:current_model"
    REDIS_KEY_PRIMARY_FAILURES = "llm:primary_failures"
    REDIS_KEY_BACKUP_FAILURES = "llm:backup_failures"
    REDIS_KEY_LAST_SWITCH_TIME = "llm:last_switch_time"
    REDIS_KEY_HEALTH_STATUS = "llm:health_status"

    def __init__(self):
        self.redis_client: Optional[aioredis.Redis] = None
        self._health_check_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """初始化负载均衡器"""
        try:
            # 连接Redis
            self.redis_client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )

            # 检查当前模型状态
            current_model = await self.redis_client.get(self.REDIS_KEY_CURRENT_MODEL)
            if not current_model:
                # 默认使用主模型
                await self.redis_client.set(self.REDIS_KEY_CURRENT_MODEL, self.PRIMARY_MODEL)
                logger.info(f"初始化LLM负载均衡器，默认使用主模型: {self.PRIMARY_MODEL}")
            else:
                logger.info(f"LLM负载均衡器已初始化，当前模型: {current_model}")

            # 启动健康检查任务
            # self._health_check_task = asyncio.create_task(self._health_check_loop())

        except Exception as e:
            logger.error(f"初始化LLM负载均衡器失败: {e}")
            raise

    async def close(self):
        """关闭负载均衡器"""
        if self._health_check_task:
            self._health_check_task.cancel()
        if self.redis_client:
            await self.redis_client.close()

    async def get_current_model(self) -> str:
        """获取当前使用的模型"""
        if not self.redis_client:
            await self.initialize()

        model = await self.redis_client.get(self.REDIS_KEY_CURRENT_MODEL)
        return model or self.PRIMARY_MODEL

    async def record_success(self, model: str):
        """记录成功调用"""
        if not self.redis_client:
            await self.initialize()

        # 重置失败计数
        if model == self.PRIMARY_MODEL:
            await self.redis_client.set(self.REDIS_KEY_PRIMARY_FAILURES, 0)
        else:
            await self.redis_client.set(self.REDIS_KEY_BACKUP_FAILURES, 0)

        logger.debug(f"模型 {model} 调用成功，失败计数已重置")

    async def record_failure(self, model: str) -> bool:
        """
        记录失败调用
        返回是否需要切换模型
        """
        if not self.redis_client:
            await self.initialize()

        # 增加失败计数
        if model == self.PRIMARY_MODEL:
            failures = await self.redis_client.incr(self.REDIS_KEY_PRIMARY_FAILURES)
            await self.redis_client.expire(self.REDIS_KEY_PRIMARY_FAILURES, self.FAILURE_RESET_TIME)
        else:
            failures = await self.redis_client.incr(self.REDIS_KEY_BACKUP_FAILURES)
            await self.redis_client.expire(self.REDIS_KEY_BACKUP_FAILURES, self.FAILURE_RESET_TIME)

        logger.warning(f"模型 {model} 调用失败，当前失败次数: {failures}")

        # 检查是否需要切换
        if failures >= self.MAX_FAILURES:
            await self._switch_model(model)
            return True

        return False

    async def _switch_model(self, failed_model: str):
        """切换模型"""
        if not self.redis_client:
            await self.initialize()

        # 确定目标模型
        if failed_model == self.PRIMARY_MODEL:
            target_model = self.BACKUP_MODEL
        else:
            target_model = self.PRIMARY_MODEL

        # 切换模型
        await self.redis_client.set(self.REDIS_KEY_CURRENT_MODEL, target_model)
        await self.redis_client.set(
            self.REDIS_KEY_LAST_SWITCH_TIME,
            datetime.now().isoformat()
        )

        logger.warning(f"模型切换: {failed_model} -> {target_model}")

    async def manual_switch(self, target_model: str):
        """手动切换模型"""
        if target_model not in [self.PRIMARY_MODEL, self.BACKUP_MODEL]:
            raise ValueError(f"无效的模型名称: {target_model}")

        if not self.redis_client:
            await self.initialize()

        await self.redis_client.set(self.REDIS_KEY_CURRENT_MODEL, target_model)
        await self.redis_client.set(
            self.REDIS_KEY_LAST_SWITCH_TIME,
            datetime.now().isoformat()
        )

        # 重置失败计数
        await self.redis_client.set(self.REDIS_KEY_PRIMARY_FAILURES, 0)
        await self.redis_client.set(self.REDIS_KEY_BACKUP_FAILURES, 0)

        logger.info(f"手动切换模型至: {target_model}")

    async def get_status(self) -> Dict[str, Any]:
        """获取负载均衡器状态"""
        if not self.redis_client:
            await self.initialize()

        current_model = await self.redis_client.get(self.REDIS_KEY_CURRENT_MODEL)
        primary_failures = await self.redis_client.get(self.REDIS_KEY_PRIMARY_FAILURES)
        backup_failures = await self.redis_client.get(self.REDIS_KEY_BACKUP_FAILURES)
        last_switch_time = await self.redis_client.get(self.REDIS_KEY_LAST_SWITCH_TIME)

        return {
            "current_model": current_model or self.PRIMARY_MODEL,
            "primary_model": self.PRIMARY_MODEL,
            "backup_model": self.BACKUP_MODEL,
            "primary_failures": int(primary_failures or 0),
            "backup_failures": int(backup_failures or 0),
            "max_failures": self.MAX_FAILURES,
            "last_switch_time": last_switch_time,
            "health_check_interval": self.HEALTH_CHECK_INTERVAL
        }

    async def _health_check_loop(self):
        """健康检查循环（后台任务）"""
        while True:
            try:
                await asyncio.sleep(self.HEALTH_CHECK_INTERVAL)
                await self._perform_health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"健康检查失败: {e}")

    async def _perform_health_check(self):
        """执行健康检查"""
        # TODO: 实现实际的健康检查逻辑
        # 可以发送简单的测试请求到各个模型
        pass


# 全局单例
_balancer_instance: Optional[LLMBalancer] = None


async def get_llm_balancer() -> LLMBalancer:
    """获取LLM负载均衡器单例"""
    global _balancer_instance
    if _balancer_instance is None:
        _balancer_instance = LLMBalancer()
        await _balancer_instance.initialize()
    return _balancer_instance
