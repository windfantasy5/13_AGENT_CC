"""
知识库检索API
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from app.services.rag_service import RAGService
from app.api.v1.auth import get_current_user
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class SearchRequest(BaseModel):
    """检索请求"""
    query: str = Field(..., description="查询文本", min_length=1, max_length=500)
    top_k: int = Field(5, description="返回结果数量", ge=1, le=20)
    document_id: Optional[int] = Field(None, description="指定文档ID")
    use_cache: bool = Field(True, description="是否使用缓存")


class SearchResponse(BaseModel):
    """检索响应"""
    query: str
    results: list
    total: int


@router.post("/search", response_model=dict)
async def search_knowledge(
    request: SearchRequest,
    current_user: User = Depends(get_current_user)
):
    """
    知识库检索

    检索向量数据库中的相关内容
    """
    try:
        rag_service = RAGService()

        # 执行检索
        results = await rag_service.search_knowledge(
            query=request.query,
            top_k=request.top_k,
            document_id=request.document_id,
            use_cache=request.use_cache
        )

        # 构建RAG上下文
        context = rag_service.build_rag_context(results["results"])

        return {
            "code": 200,
            "message": "success",
            "data": {
                "query": results["query"],
                "results": results["results"],
                "total": results["total"],
                "context": context
            }
        }

    except Exception as e:
        logger.error(f"知识库检索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cache", response_model=dict)
async def clear_search_cache(
    current_user: User = Depends(get_current_user)
):
    """
    清除检索缓存
    """
    try:
        rag_service = RAGService()
        deleted = await rag_service.clear_cache()

        return {
            "code": 200,
            "message": "success",
            "data": {
                "deleted_keys": deleted
            }
        }

    except Exception as e:
        logger.error(f"清除缓存失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
