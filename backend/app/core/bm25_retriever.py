"""
BM25关键词检索服务
使用rank-bm25实现关键词检索，支持中文分词和增量更新
"""
import pickle
import logging
from typing import List, Dict, Optional
from rank_bm25 import BM25Okapi
from redis import asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import DocumentChunk
from app.core.advanced_tokenizer import AdvancedTokenizer
from app.config.settings import settings

logger = logging.getLogger(__name__)


class BM25Retriever:
    """BM25检索器"""

    def __init__(self):
        self.redis_client = None
        self.bm25_index = None
        self.corpus_ids = []  # 存储chunk_id列表
        self.corpus_tokens = []  # 存储分词结果（用于增量更新）
        self.index_key = "bm25:index"
        self.corpus_key = "bm25:corpus_ids"
        self.tokens_key = "bm25:corpus_tokens"
        self.tokenizer = AdvancedTokenizer()

    async def get_redis_client(self):
        """获取Redis客户端"""
        if self.redis_client is None:
            self.redis_client = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=False  # BM25索引需要二进制存储
            )
        return self.redis_client

    def tokenize(self, text: str) -> List[str]:
        """
        中文分词（使用高级分词器）

        Args:
            text: 输入文本

        Returns:
            分词结果列表
        """
        return self.tokenizer.tokenize(text, use_pos_filter=True)

    async def build_index(self, db: AsyncSession, force_rebuild: bool = False):
        """
        构建BM25索引

        Args:
            db: 数据库会话
            force_rebuild: 是否强制重建索引
        """
        # 检查是否已有索引
        if not force_rebuild:
            if await self._load_index_from_redis():
                logger.info(f"从Redis加载BM25索引，文档数: {len(self.corpus_ids)}")
                return

        logger.info("开始构建BM25索引...")

        # 从数据库获取所有文档分块
        stmt = select(DocumentChunk).where(DocumentChunk.vector_id.isnot(None))
        result = await db.execute(stmt)
        chunks = result.scalars().all()

        if not chunks:
            logger.warning("没有找到已向量化的文档分块")
            return

        # 准备语料库
        corpus = []
        corpus_ids = []

        for chunk in chunks:
            tokens = self.tokenize(chunk.content)
            corpus.append(tokens)
            corpus_ids.append(chunk.id)

        # 构建BM25索引
        self.bm25_index = BM25Okapi(corpus)
        self.corpus_ids = corpus_ids
        self.corpus_tokens = corpus  # 保存分词结果

        # 保存到Redis
        await self._save_index_to_redis()

        logger.info(f"BM25索引构建完成，文档数: {len(corpus_ids)}")

    async def _save_index_to_redis(self):
        """保存索引到Redis"""
        try:
            redis = await self.get_redis_client()

            # 序列化BM25索引
            index_data = pickle.dumps(self.bm25_index)
            corpus_data = pickle.dumps(self.corpus_ids)
            tokens_data = pickle.dumps(self.corpus_tokens)

            # 保存到Redis
            await redis.set(self.index_key, index_data)
            await redis.set(self.corpus_key, corpus_data)
            await redis.set(self.tokens_key, tokens_data)

            logger.info("BM25索引已保存到Redis")
        except Exception as e:
            logger.error(f"保存BM25索引到Redis失败: {e}")

    async def _load_index_from_redis(self) -> bool:
        """从Redis加载索引"""
        try:
            redis = await self.get_redis_client()

            # 加载索引数据
            index_data = await redis.get(self.index_key)
            corpus_data = await redis.get(self.corpus_key)
            tokens_data = await redis.get(self.tokens_key)

            if index_data and corpus_data:
                self.bm25_index = pickle.loads(index_data)
                self.corpus_ids = pickle.loads(corpus_data)

                # tokens_data可能不存在（旧版本）
                if tokens_data:
                    self.corpus_tokens = pickle.loads(tokens_data)
                else:
                    self.corpus_tokens = []

                return True

            return False
        except Exception as e:
            logger.error(f"从Redis加载BM25索引失败: {e}")
            return False

    async def add_documents_incremental(
        self,
        chunk_ids: List[int],
        contents: List[str]
    ) -> bool:
        """
        增量添加文档到索引

        Args:
            chunk_ids: 分块ID列表
            contents: 分块内容列表

        Returns:
            是否成功
        """
        try:
            # 分词
            new_tokens = [self.tokenize(content) for content in contents]

            # 添加到语料库
            self.corpus_ids.extend(chunk_ids)
            self.corpus_tokens.extend(new_tokens)

            # 重建索引（BM25Okapi不支持真正的增量，需要重建）
            self.bm25_index = BM25Okapi(self.corpus_tokens)

            # 保存到Redis
            await self._save_index_to_redis()

            logger.info(f"增量添加 {len(chunk_ids)} 个文档到BM25索引")
            return True

        except Exception as e:
            logger.error(f"增量添加文档失败: {e}")
            return False

    async def delete_documents(self, chunk_ids: List[int]) -> bool:
        """
        从索引中删除文档

        Args:
            chunk_ids: 要删除的分块ID列表

        Returns:
            是否成功
        """
        try:
            # 找到要删除的索引位置
            indices_to_remove = []
            for chunk_id in chunk_ids:
                if chunk_id in self.corpus_ids:
                    idx = self.corpus_ids.index(chunk_id)
                    indices_to_remove.append(idx)

            if not indices_to_remove:
                logger.warning(f"未找到要删除的文档: {chunk_ids}")
                return False

            # 从后往前删除（避免索引变化）
            for idx in sorted(indices_to_remove, reverse=True):
                del self.corpus_ids[idx]
                if idx < len(self.corpus_tokens):
                    del self.corpus_tokens[idx]

            # 重建索引
            if self.corpus_tokens:
                self.bm25_index = BM25Okapi(self.corpus_tokens)
            else:
                self.bm25_index = None

            # 保存到Redis
            await self._save_index_to_redis()

            logger.info(f"从BM25索引删除 {len(indices_to_remove)} 个文档")
            return True

        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False

    async def search(
        self,
        query: str,
        top_k: int = 5,
        db: Optional[AsyncSession] = None
    ) -> List[Dict]:
        """
        BM25检索

        Args:
            query: 查询文本
            top_k: 返回结果数量
            db: 数据库会话（用于获取完整文档信息）

        Returns:
            检索结果列表
        """
        # 确保索引已加载
        if self.bm25_index is None:
            logger.warning("BM25索引未初始化")
            return []

        # 分词
        query_tokens = self.tokenize(query)

        if not query_tokens:
            logger.warning("查询分词结果为空")
            return []

        # BM25检索
        scores = self.bm25_index.get_scores(query_tokens)

        # 获取top_k结果
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        results = []
        for idx in top_indices:
            chunk_id = self.corpus_ids[idx]
            score = float(scores[idx])

            # 如果提供了数据库会话，获取完整信息
            chunk_info = {"chunk_id": chunk_id, "score": score}

            if db:
                stmt = select(DocumentChunk).where(DocumentChunk.id == chunk_id)
                result = await db.execute(stmt)
                chunk = result.scalar_one_or_none()

                if chunk:
                    chunk_info.update({
                        "content": chunk.content,
                        "document_id": chunk.document_id,
                        "metadata": {
                            "chunk_index": chunk.chunk_index,
                            "document_id": chunk.document_id
                        }
                    })

            results.append(chunk_info)

        logger.info(f"BM25检索完成，查询: {query}, 返回: {len(results)} 个结果")
        return results

    async def add_document(self, chunk_id: int, content: str):
        """
        添加单个文档到索引

        Args:
            chunk_id: 文档分块ID
            content: 文档内容
        """
        if self.bm25_index is None:
            logger.warning("BM25索引未初始化，无法添加文档")
            return

        tokens = self.tokenize(content)

        # 更新索引（需要重建）
        # 注意：BM25Okapi不支持增量更新，需要重建索引
        logger.warning("BM25索引不支持增量更新，请调用build_index重建索引")

    async def delete_document(self, chunk_id: int):
        """
        从索引中删除文档

        Args:
            chunk_id: 文档分块ID
        """
        if chunk_id in self.corpus_ids:
            logger.warning("BM25索引不支持增量删除，请调用build_index重建索引")

    async def clear_index(self):
        """清除索引"""
        try:
            redis = await self.get_redis_client()
            await redis.delete(self.index_key, self.corpus_key)
            self.bm25_index = None
            self.corpus_ids = []
            logger.info("BM25索引已清除")
        except Exception as e:
            logger.error(f"清除BM25索引失败: {e}")

    async def get_index_stats(self) -> Dict:
        """
        获取索引统计信息

        Returns:
            统计信息字典
        """
        return {
            "total_documents": len(self.corpus_ids) if self.corpus_ids else 0,
            "index_loaded": self.bm25_index is not None
        }

    async def close(self):
        """关闭Redis连接"""
        if self.redis_client:
            await self.redis_client.close()
