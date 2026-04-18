"""
测试改进后的文档上传功能
验证同时构建BM25索引和向量数据库
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import AsyncSessionLocal
from app.services.document_service import DocumentService
from app.models.document import Document
from app.core.bm25_retriever import BM25Retriever
from app.core.vector_store import VectorStore
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_upload_and_indexing():
    """测试文档上传和双索引构建"""
    logger.info("=" * 60)
    logger.info("测试：文档上传 + 双索引构建")
    logger.info("=" * 60)

    async with AsyncSessionLocal() as db:
        doc_service = DocumentService()

        # 创建测试文档
        test_content = """
        机器学习是人工智能的一个重要分支。
        深度学习是机器学习的子领域，使用神经网络进行学习。
        自然语言处理是让计算机理解和生成人类语言的技术。
        计算机视觉让机器能够理解和分析图像和视频。
        强化学习通过与环境交互来学习最优策略。
        """

        # 模拟文件上传
        logger.info("\n步骤1: 创建测试文档...")
        document = Document(
            user_id=1,
            title="测试文档-双索引",
            file_type="txt",
            file_path="/tmp/test.txt",
            file_hash="test_hash_123",
            file_size=len(test_content),
            status='pending'
        )
        db.add(document)
        await db.commit()
        await db.refresh(document)
        logger.info(f"文档创建成功，ID: {document.id}")

        # 保存分块并构建双索引
        logger.info("\n步骤2: 保存分块并构建双索引...")
        params = {
            "max_chunk_size": 100,
            "min_chunk_size": 20,
            "overlap_size": 10
        }
        chunk_count = await doc_service.save_chunks(
            document_id=document.id,
            text=test_content,
            params=params,
            db=db
        )
        logger.info(f"分块数量: {chunk_count}")

        # 验证向量索引
        logger.info("\n步骤3: 验证向量索引...")
        vector_store = VectorStore()
        vector_stats = vector_store.get_collection_stats()
        logger.info(f"向量库统计: {vector_stats}")

        # 测试向量检索
        vector_results = vector_store.search_similar("机器学习", top_k=2)
        logger.info(f"向量检索结果数: {len(vector_results['results'])}")
        if vector_results['results']:
            logger.info(f"Top1 距离: {vector_results['results'][0]['distance']:.4f}")

        # 验证BM25索引
        logger.info("\n步骤4: 验证BM25索引...")
        bm25_retriever = BM25Retriever()
        await bm25_retriever._load_index_from_redis()
        bm25_stats = await bm25_retriever.get_index_stats()
        logger.info(f"BM25索引统计: {bm25_stats}")

        # 测试BM25检索
        bm25_results = await bm25_retriever.search("机器学习", top_k=2, db=db)
        logger.info(f"BM25检索结果数: {len(bm25_results)}")
        if bm25_results:
            logger.info(f"Top1 分数: {bm25_results[0]['score']:.4f}")

        await bm25_retriever.close()

        # 测试混合检索
        logger.info("\n步骤5: 测试混合检索...")
        from app.services.hybrid_search_service import HybridSearchService
        hybrid_service = HybridSearchService()
        await hybrid_service.initialize(db, force_rebuild=False)

        hybrid_results = await hybrid_service.hybrid_search(
            query="机器学习",
            top_k=2,
            bm25_weight=0.5,
            vector_weight=0.5,
            db=db
        )
        logger.info(f"混合检索结果数: {hybrid_results['total']}")
        if hybrid_results['results']:
            top_result = hybrid_results['results'][0]
            logger.info(f"Top1 RRF分数: {top_result['rrf_score']:.4f}")
            logger.info(f"Top1 来源: {', '.join(top_result['sources'])}")

        await hybrid_service.close()

        logger.info("\n✅ 测试完成！")
        logger.info("=" * 60)


async def test_delete_document():
    """测试删除文档（同时删除双索引）"""
    logger.info("\n" + "=" * 60)
    logger.info("测试：删除文档 + 双索引删除")
    logger.info("=" * 60)

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        from app.models.document import DocumentChunk

        # 查找测试文档
        result = await db.execute(
            select(Document).where(Document.title == "测试文档-双索引")
        )
        document = result.scalar_one_or_none()

        if not document:
            logger.warning("未找到测试文档")
            return

        doc_id = document.id
        logger.info(f"找到测试文档，ID: {doc_id}")

        # 获取分块ID
        chunks_result = await db.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == doc_id)
        )
        chunks = chunks_result.scalars().all()
        chunk_ids = [chunk.id for chunk in chunks]
        logger.info(f"文档分块数: {len(chunk_ids)}")

        # 删除前的索引状态
        logger.info("\n删除前的索引状态:")
        vector_store = VectorStore()
        vector_stats_before = vector_store.get_collection_stats()
        logger.info(f"向量库文档数: {vector_stats_before['total_chunks']}")

        bm25_retriever = BM25Retriever()
        await bm25_retriever._load_index_from_redis()
        bm25_stats_before = await bm25_retriever.get_index_stats()
        logger.info(f"BM25索引文档数: {bm25_stats_before['total_documents']}")

        # 删除向量索引
        logger.info("\n删除向量索引...")
        vector_store.delete_document_chunks(doc_id)

        # 删除BM25索引
        logger.info("删除BM25索引...")
        await bm25_retriever.delete_documents(chunk_ids)

        # 删除数据库记录
        logger.info("删除数据库记录...")
        await db.delete(document)
        await db.commit()

        # 删除后的索引状态
        logger.info("\n删除后的索引状态:")
        vector_stats_after = vector_store.get_collection_stats()
        logger.info(f"向量库文档数: {vector_stats_after['total_chunks']}")

        bm25_stats_after = await bm25_retriever.get_index_stats()
        logger.info(f"BM25索引文档数: {bm25_stats_after['total_documents']}")

        await bm25_retriever.close()

        logger.info("\n✅ 删除测试完成！")
        logger.info("=" * 60)


async def test_tokenizer():
    """测试高级分词器"""
    logger.info("\n" + "=" * 60)
    logger.info("测试：高级分词器")
    logger.info("=" * 60)

    from app.core.advanced_tokenizer import AdvancedTokenizer

    tokenizer = AdvancedTokenizer()

    test_texts = [
        "机器学习是人工智能的一个重要分支",
        "深度学习使用神经网络进行学习",
        "自然语言处理让计算机理解人类语言"
    ]

    for text in test_texts:
        tokens = tokenizer.tokenize(text, use_pos_filter=True)
        logger.info(f"\n原文: {text}")
        logger.info(f"分词结果: {' / '.join(tokens)}")
        logger.info(f"词数: {len(tokens)}")

    logger.info("\n✅ 分词器测试完成！")
    logger.info("=" * 60)


async def run_all_tests():
    """运行所有测试"""
    try:
        # 测试1: 高级分词器
        await test_tokenizer()

        # 测试2: 文档上传和双索引构建
        await test_upload_and_indexing()

        # 测试3: 删除文档和双索引
        await test_delete_document()

        logger.info("\n" + "=" * 60)
        logger.info("🎉 所有测试完成！")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"\n❌ 测试失败: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(run_all_tests())
