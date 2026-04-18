"""
混合检索服务
融合BM25关键词检索和向量语义检索
使用RRF (Reciprocal Rank Fusion) 算法进行结果融合
"""
import logging
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.bm25_retriever import BM25Retriever
from app.core.vector_store import VectorStore

logger = logging.getLogger(__name__)


class HybridSearchService:
    """混合检索服务"""

    def __init__(self):
        self.bm25_retriever = BM25Retriever()
        self.vector_store = VectorStore()

    async def initialize(self, db: AsyncSession, force_rebuild: bool = False):
        """
        初始化检索器

        Args:
            db: 数据库会话
            force_rebuild: 是否强制重建BM25索引
        """
        await self.bm25_retriever.build_index(db, force_rebuild)
        logger.info("混合检索服务初始化完成")

    async def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        bm25_weight: float = 0.5,
        vector_weight: float = 0.5,
        document_id: Optional[int] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict:
        """
        混合检索（BM25 + 向量检索）

        Args:
            query: 查询文本
            top_k: 返回结果数量
            bm25_weight: BM25权重（0-1）
            vector_weight: 向量检索权重（0-1）
            document_id: 指定文档ID（可选）
            db: 数据库会话

        Returns:
            融合后的检索结果
        """
        # 参数验证
        if bm25_weight + vector_weight != 1.0:
            logger.warning(f"权重之和不为1，自动归一化: bm25={bm25_weight}, vector={vector_weight}")
            total = bm25_weight + vector_weight
            bm25_weight = bm25_weight / total
            vector_weight = vector_weight / total

        # 1. BM25检索
        bm25_results = []
        try:
            bm25_results = await self.bm25_retriever.search(
                query=query,
                top_k=top_k * 2,  # 获取更多结果用于融合
                db=db
            )
            logger.info(f"BM25检索返回 {len(bm25_results)} 个结果")
        except Exception as e:
            logger.error(f"BM25检索失败: {e}")

        # 2. 向量检索
        vector_results = []
        try:
            filter_metadata = {"document_id": document_id} if document_id else None
            vector_search_result = self.vector_store.search_similar(
                query=query,
                top_k=top_k * 2,
                filter_metadata=filter_metadata
            )
            vector_results = vector_search_result.get("results", [])
            logger.info(f"向量检索返回 {len(vector_results)} 个结果")
        except Exception as e:
            logger.error(f"向量检索失败: {e}")

        # 3. 使用RRF融合结果
        fused_results = self._rrf_fusion(
            bm25_results=bm25_results,
            vector_results=vector_results,
            bm25_weight=bm25_weight,
            vector_weight=vector_weight,
            k=60  # RRF参数
        )

        # 4. 返回top_k结果
        final_results = fused_results[:top_k]

        logger.info(f"混合检索完成，最终返回 {len(final_results)} 个结果")

        return {
            "query": query,
            "results": final_results,
            "total": len(final_results),
            "method": "hybrid",
            "weights": {
                "bm25": bm25_weight,
                "vector": vector_weight
            }
        }

    def _rrf_fusion(
        self,
        bm25_results: List[Dict],
        vector_results: List[Dict],
        bm25_weight: float = 0.5,
        vector_weight: float = 0.5,
        k: int = 60
    ) -> List[Dict]:
        """
        RRF (Reciprocal Rank Fusion) 算法融合结果

        RRF公式: score = sum(weight / (k + rank))

        Args:
            bm25_results: BM25检索结果
            vector_results: 向量检索结果
            bm25_weight: BM25权重
            vector_weight: 向量权重
            k: RRF参数（通常为60）

        Returns:
            融合后的结果列表
        """
        # 使用chunk_id作为唯一标识
        scores = {}
        chunk_data = {}

        # 处理BM25结果
        for rank, result in enumerate(bm25_results, start=1):
            chunk_id = result.get("chunk_id")
            if chunk_id:
                rrf_score = bm25_weight / (k + rank)
                scores[chunk_id] = scores.get(chunk_id, 0) + rrf_score

                # 保存完整数据（如果还没有）
                if chunk_id not in chunk_data:
                    chunk_data[chunk_id] = {
                        "chunk_id": chunk_id,
                        "content": result.get("content", ""),
                        "document_id": result.get("document_id"),
                        "metadata": result.get("metadata", {}),
                        "bm25_score": result.get("score", 0),
                        "vector_score": None,
                        "sources": ["bm25"]
                    }
                else:
                    chunk_data[chunk_id]["bm25_score"] = result.get("score", 0)
                    chunk_data[chunk_id]["sources"].append("bm25")

        # 处理向量检索结果
        for rank, result in enumerate(vector_results, start=1):
            # 从向量ID提取chunk_id
            vector_id = result.get("id", "")
            if vector_id.startswith("chunk_"):
                chunk_id = int(vector_id.replace("chunk_", ""))
            else:
                continue

            rrf_score = vector_weight / (k + rank)
            scores[chunk_id] = scores.get(chunk_id, 0) + rrf_score

            # 保存完整数据
            if chunk_id not in chunk_data:
                chunk_data[chunk_id] = {
                    "chunk_id": chunk_id,
                    "content": result.get("content", ""),
                    "document_id": result.get("metadata", {}).get("document_id"),
                    "metadata": result.get("metadata", {}),
                    "bm25_score": None,
                    "vector_score": 1.0 - result.get("distance", 0),  # 距离转相似度
                    "sources": ["vector"]
                }
            else:
                chunk_data[chunk_id]["vector_score"] = 1.0 - result.get("distance", 0)
                if "vector" not in chunk_data[chunk_id]["sources"]:
                    chunk_data[chunk_id]["sources"].append("vector")

        # 按RRF分数排序
        sorted_chunks = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # 构建最终结果
        fused_results = []
        for chunk_id, rrf_score in sorted_chunks:
            if chunk_id in chunk_data:
                result = chunk_data[chunk_id].copy()
                result["rrf_score"] = rrf_score
                result["score"] = rrf_score  # 统一使用score字段
                fused_results.append(result)

        return fused_results

    async def bm25_only_search(
        self,
        query: str,
        top_k: int = 5,
        db: Optional[AsyncSession] = None
    ) -> Dict:
        """
        仅使用BM25检索

        Args:
            query: 查询文本
            top_k: 返回结果数量
            db: 数据库会话

        Returns:
            检索结果
        """
        results = await self.bm25_retriever.search(query, top_k, db)

        return {
            "query": query,
            "results": results,
            "total": len(results),
            "method": "bm25"
        }

    async def vector_only_search(
        self,
        query: str,
        top_k: int = 5,
        document_id: Optional[int] = None
    ) -> Dict:
        """
        仅使用向量检索

        Args:
            query: 查询文本
            top_k: 返回结果数量
            document_id: 指定文档ID

        Returns:
            检索结果
        """
        filter_metadata = {"document_id": document_id} if document_id else None
        results = self.vector_store.search_similar(
            query=query,
            top_k=top_k,
            filter_metadata=filter_metadata
        )

        # 统一字段名：将distance转换为score（相似度 = 1 - distance）
        formatted_results = []
        for r in results.get("results", []):
            result = r.copy()
            if "distance" in result and "score" not in result:
                # ChromaDB返回的是距离，转换为相似度分数
                result["score"] = 1.0 - result["distance"]
            formatted_results.append(result)

        return {
            "query": query,
            "results": formatted_results,
            "total": len(formatted_results),
            "method": "vector"
        }

    async def rebuild_bm25_index(self, db: AsyncSession):
        """
        重建BM25索引

        Args:
            db: 数据库会话
        """
        await self.bm25_retriever.build_index(db, force_rebuild=True)
        logger.info("BM25索引重建完成")

    async def get_stats(self) -> Dict:
        """
        获取检索器统计信息

        Returns:
            统计信息
        """
        bm25_stats = await self.bm25_retriever.get_index_stats()
        vector_stats = self.vector_store.get_collection_stats()

        return {
            "bm25": bm25_stats,
            "vector": vector_stats
        }

    async def close(self):
        """关闭连接"""
        await self.bm25_retriever.close()
