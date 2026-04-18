"""
混合检索测试脚本
测试BM25检索、向量检索和混合检索的功能和性能
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import AsyncSessionLocal
from app.services.hybrid_search_service import HybridSearchService
from app.core.bm25_retriever import BM25Retriever
from app.core.vector_store import VectorStore
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_bm25_retriever():
    """测试BM25检索器"""
    logger.info("=" * 60)
    logger.info("测试1: BM25检索器")
    logger.info("=" * 60)

    async with AsyncSessionLocal() as db:
        retriever = BM25Retriever()

        # 构建索引
        logger.info("步骤1: 构建BM25索引...")
        await retriever.build_index(db, force_rebuild=True)

        # 获取统计信息
        stats = await retriever.get_index_stats()
        logger.info(f"索引统计: {stats}")

        # 测试检索
        test_queries = [
            "机器学习是什么",
            "人工智能的应用",
            "深度学习算法",
            "神经网络原理"
        ]

        for query in test_queries:
            logger.info(f"\n查询: {query}")
            results = await retriever.search(query, top_k=3, db=db)

            if results:
                for i, result in enumerate(results, 1):
                    logger.info(f"  结果{i}:")
                    logger.info(f"    Chunk ID: {result['chunk_id']}")
                    logger.info(f"    BM25分数: {result['score']:.4f}")
                    content = result.get('content', '')
                    logger.info(f"    内容预览: {content[:100]}...")
            else:
                logger.warning(f"  未找到相关结果")

        await retriever.close()

    logger.info("\n✅ BM25检索器测试完成\n")


async def test_vector_retriever():
    """测试向量检索器"""
    logger.info("=" * 60)
    logger.info("测试2: 向量检索器")
    logger.info("=" * 60)

    vector_store = VectorStore()

    # 获取统计信息
    stats = vector_store.get_collection_stats()
    logger.info(f"向量库统计: {stats}")

    # 测试检索
    test_queries = [
        "机器学习是什么",
        "人工智能的应用",
        "深度学习算法",
        "神经网络原理"
    ]

    for query in test_queries:
        logger.info(f"\n查询: {query}")
        results = vector_store.search_similar(query, top_k=3)

        if results['results']:
            for i, result in enumerate(results['results'], 1):
                logger.info(f"  结果{i}:")
                logger.info(f"    向量ID: {result['id']}")
                logger.info(f"    距离: {result['distance']:.4f}")
                logger.info(f"    相似度: {1 - result['distance']:.4f}")
                content = result.get('content', '')
                logger.info(f"    内容预览: {content[:100]}...")
        else:
            logger.warning(f"  未找到相关结果")

    logger.info("\n✅ 向量检索器测试完成\n")


async def test_hybrid_search():
    """测试混合检索"""
    logger.info("=" * 60)
    logger.info("测试3: 混合检索")
    logger.info("=" * 60)

    async with AsyncSessionLocal() as db:
        hybrid_service = HybridSearchService()

        # 初始化
        logger.info("步骤1: 初始化混合检索服务...")
        await hybrid_service.initialize(db, force_rebuild=False)

        # 获取统计信息
        stats = await hybrid_service.get_stats()
        logger.info(f"检索器统计: {stats}")

        # 测试不同权重配置
        test_configs = [
            {"bm25_weight": 0.5, "vector_weight": 0.5, "name": "均衡模式"},
            {"bm25_weight": 0.7, "vector_weight": 0.3, "name": "关键词优先"},
            {"bm25_weight": 0.3, "vector_weight": 0.7, "name": "语义优先"}
        ]

        test_query = "机器学习的基本原理"

        for config in test_configs:
            logger.info(f"\n配置: {config['name']} (BM25={config['bm25_weight']}, Vector={config['vector_weight']})")
            logger.info(f"查询: {test_query}")

            results = await hybrid_service.hybrid_search(
                query=test_query,
                top_k=3,
                bm25_weight=config['bm25_weight'],
                vector_weight=config['vector_weight'],
                db=db
            )

            logger.info(f"返回结果数: {results['total']}")

            for i, result in enumerate(results['results'], 1):
                logger.info(f"  结果{i}:")
                logger.info(f"    Chunk ID: {result['chunk_id']}")
                logger.info(f"    RRF分数: {result['rrf_score']:.4f}")
                logger.info(f"    BM25分数: {result.get('bm25_score', 'N/A')}")
                logger.info(f"    向量分数: {result.get('vector_score', 'N/A')}")
                logger.info(f"    来源: {', '.join(result['sources'])}")
                content = result.get('content', '')
                logger.info(f"    内容预览: {content[:100]}...")

        await hybrid_service.close()

    logger.info("\n✅ 混合检索测试完成\n")


async def test_comparison():
    """对比测试：BM25 vs 向量 vs 混合"""
    logger.info("=" * 60)
    logger.info("测试4: 检索方法对比")
    logger.info("=" * 60)

    async with AsyncSessionLocal() as db:
        hybrid_service = HybridSearchService()
        await hybrid_service.initialize(db, force_rebuild=False)

        test_queries = [
            "机器学习算法",
            "深度神经网络",
            "人工智能应用"
        ]

        for query in test_queries:
            logger.info(f"\n查询: {query}")
            logger.info("-" * 60)

            # BM25检索
            bm25_results = await hybrid_service.bm25_only_search(query, top_k=3, db=db)
            logger.info(f"BM25检索: 返回 {bm25_results['total']} 个结果")
            if bm25_results['results']:
                top_result = bm25_results['results'][0]
                logger.info(f"  Top1 分数: {top_result['score']:.4f}")
                logger.info(f"  Top1 内容: {top_result.get('content', '')[:80]}...")

            # 向量检索
            vector_results = await hybrid_service.vector_only_search(query, top_k=3)
            logger.info(f"向量检索: 返回 {vector_results['total']} 个结果")
            if vector_results['results']:
                top_result = vector_results['results'][0]
                logger.info(f"  Top1 距离: {top_result.get('distance', 0):.4f}")
                logger.info(f"  Top1 内容: {top_result.get('content', '')[:80]}...")

            # 混合检索
            hybrid_results = await hybrid_service.hybrid_search(
                query, top_k=3, bm25_weight=0.5, vector_weight=0.5, db=db
            )
            logger.info(f"混合检索: 返回 {hybrid_results['total']} 个结果")
            if hybrid_results['results']:
                top_result = hybrid_results['results'][0]
                logger.info(f"  Top1 RRF分数: {top_result['rrf_score']:.4f}")
                logger.info(f"  Top1 来源: {', '.join(top_result['sources'])}")
                logger.info(f"  Top1 内容: {top_result.get('content', '')[:80]}...")

        await hybrid_service.close()

    logger.info("\n✅ 对比测试完成\n")


async def test_rebuild_index():
    """测试索引重建"""
    logger.info("=" * 60)
    logger.info("测试5: 索引重建")
    logger.info("=" * 60)

    async with AsyncSessionLocal() as db:
        retriever = BM25Retriever()

        # 清除现有索引
        logger.info("步骤1: 清除现有索引...")
        await retriever.clear_index()

        stats = await retriever.get_index_stats()
        logger.info(f"清除后统计: {stats}")

        # 重建索引
        logger.info("步骤2: 重建索引...")
        await retriever.build_index(db, force_rebuild=True)

        stats = await retriever.get_index_stats()
        logger.info(f"重建后统计: {stats}")

        # 验证检索功能
        logger.info("步骤3: 验证检索功能...")
        results = await retriever.search("测试查询", top_k=3, db=db)
        logger.info(f"检索结果数: {len(results)}")

        await retriever.close()

    logger.info("\n✅ 索引重建测试完成\n")


async def run_all_tests():
    """运行所有测试"""
    logger.info("\n" + "=" * 60)
    logger.info("开始混合检索系统测试")
    logger.info("=" * 60 + "\n")

    try:
        # 测试1: BM25检索器
        await test_bm25_retriever()

        # 测试2: 向量检索器
        await test_vector_retriever()

        # 测试3: 混合检索
        await test_hybrid_search()

        # 测试4: 对比测试
        await test_comparison()

        # 测试5: 索引重建
        await test_rebuild_index()

        logger.info("\n" + "=" * 60)
        logger.info("🎉 所有测试完成！")
        logger.info("=" * 60 + "\n")

    except Exception as e:
        logger.error(f"\n❌ 测试失败: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(run_all_tests())
