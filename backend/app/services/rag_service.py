"""
RAG检索服务
支持混合检索（BM25 + 向量检索）
"""
import hashlib
import json
from typing import List, Dict, Optional
from redis import asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.vector_store import VectorStore
from app.services.hybrid_search_service import HybridSearchService
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)


class RAGService:
    """RAG检索服务"""

    def __init__(self):
        self.vector_store = VectorStore()
        self.hybrid_search = HybridSearchService()
        self.redis_client = None
        self.cache_ttl = 7 * 24 * 3600  # 7天缓存
        self._hybrid_initialized = False

    async def get_redis_client(self):
        """获取Redis客户端"""
        if self.redis_client is None:
            self.redis_client = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
        return self.redis_client

    def _generate_cache_key(self, query: str, top_k: int, document_id: Optional[int] = None, method: str = "vector") -> str:
        """生成缓存键"""
        cache_data = f"{query}:{top_k}:{document_id}:{method}"
        query_hash = hashlib.md5(cache_data.encode()).hexdigest()
        return f"qa:cache:{query_hash}"

    async def initialize_hybrid_search(self, db: AsyncSession, force_rebuild: bool = False):
        """
        初始化混合检索服务

        Args:
            db: 数据库会话
            force_rebuild: 是否强制重建BM25索引
        """
        if not self._hybrid_initialized or force_rebuild:
            await self.hybrid_search.initialize(db, force_rebuild)
            self._hybrid_initialized = True
            logger.info("混合检索服务已初始化")

    async def search_knowledge(
        self,
        query: str,
        top_k: int = 5,
        document_id: Optional[int] = None,
        use_cache: bool = True,
        use_hybrid: bool = True,
        bm25_weight: float = 0.5,
        vector_weight: float = 0.5,
        db: Optional[AsyncSession] = None
    ) -> Dict:
        """
        检索知识库（支持混合检索）

        Args:
            query: 查询文本
            top_k: 返回结果数量
            document_id: 指定文档ID(可选)
            use_cache: 是否使用缓存
            use_hybrid: 是否使用混合检索（True=混合，False=仅向量）
            bm25_weight: BM25权重（仅混合检索时有效）
            vector_weight: 向量权重（仅混合检索时有效）
            db: 数据库会话（混合检索需要）

        Returns:
            检索结果
        """
        method = "hybrid" if use_hybrid else "vector"

        # 检查缓存
        if use_cache:
            cache_key = self._generate_cache_key(query, top_k, document_id, method)
            try:
                redis = await self.get_redis_client()
                cached_result = await redis.get(cache_key)
                if cached_result:
                    logger.info(f"从缓存获取检索结果: {cache_key}")
                    return json.loads(cached_result)
            except Exception as e:
                logger.warning(f"Redis缓存读取失败: {e}")

        # 执行检索
        try:
            if use_hybrid and db:
                # 确保混合检索已初始化
                if not self._hybrid_initialized:
                    await self.initialize_hybrid_search(db)

                # 混合检索
                results = await self.hybrid_search.hybrid_search(
                    query=query,
                    top_k=top_k,
                    bm25_weight=bm25_weight,
                    vector_weight=vector_weight,
                    document_id=document_id,
                    db=db
                )
            else:
                # 仅向量检索（保持向后兼容）
                results = await self.hybrid_search.vector_only_search(
                    query=query,
                    top_k=top_k,
                    document_id=document_id
                )

            # 缓存结果
            if use_cache:
                try:
                    redis = await self.get_redis_client()
                    await redis.setex(
                        cache_key,
                        self.cache_ttl,
                        json.dumps(results, ensure_ascii=False)
                    )
                    logger.info(f"检索结果已缓存: {cache_key}")
                except Exception as e:
                    logger.warning(f"Redis缓存写入失败: {e}")

            return results

        except Exception as e:
            logger.error(f"知识库检索失败: {e}")
            raise Exception(f"检索失败: {str(e)}")

    def build_rag_context(self, search_results: List[Dict], max_length: int = 2000) -> str:
        """
        构建RAG上下文

        Args:
            search_results: 检索结果列表
            max_length: 最大长度

        Returns:
            格式化的上下文文本
        """
        if not search_results:
            return ""

        context_parts = []
        current_length = 0

        for i, result in enumerate(search_results, 1):
            content = result.get("content", "")
            metadata = result.get("metadata", {})

            # 构建单条上下文
            context_item = f"[参考资料{i}]\n{content}\n"
            item_length = len(context_item)

            # 检查是否超过最大长度
            if current_length + item_length > max_length:
                # 截断最后一条
                remaining = max_length - current_length
                if remaining > 100:  # 至少保留100字符
                    context_item = context_item[:remaining] + "...\n"
                    context_parts.append(context_item)
                break

            context_parts.append(context_item)
            current_length += item_length

        return "\n".join(context_parts)

    def compress_rag_context(self, context: str, max_length: int = 1000) -> str:
        """
        压缩RAG上下文用于日志记录

        Args:
            context: 原始上下文
            max_length: 最大长度

        Returns:
            压缩后的上下文
        """
        if len(context) <= max_length:
            return context

        # 提取关键信息
        lines = context.split("\n")
        compressed_lines = []
        current_length = 0

        for line in lines:
            if line.startswith("[参考资料"):
                compressed_lines.append(line)
                current_length += len(line)
            elif line.strip() and current_length < max_length:
                # 保留部分内容
                remaining = max_length - current_length
                if remaining > 50:
                    if len(line) > remaining:
                        compressed_lines.append(line[:remaining] + "...")
                        break
                    else:
                        compressed_lines.append(line)
                        current_length += len(line)

        return "\n".join(compressed_lines)

    async def clear_cache(self, pattern: str = "qa:cache:*") -> int:
        """
        清除缓存

        Args:
            pattern: 缓存键模式

        Returns:
            清除的键数量
        """
        try:
            redis = await self.get_redis_client()
            keys = []
            async for key in redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted = await redis.delete(*keys)
                logger.info(f"清除了 {deleted} 个缓存键")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"清除缓存失败: {e}")
            return 0

    async def close(self):
        """关闭Redis连接"""
        if self.redis_client:
            await self.redis_client.close()
        await self.hybrid_search.close()
