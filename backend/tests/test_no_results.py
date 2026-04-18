"""
测试无资料场景的错误处理
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.rag_service import RAGService


async def test_no_results():
    """测试没有检索到结果的场景"""
    print("="*60)
    print("Test: No Retrieval Results Scenario")
    print("="*60)

    rag_service = RAGService()

    # 测试一个不太可能有结果的查询
    query = "机器人不能自动排污"

    print(f"\n查询: {query}")
    print("正在检索...")

    try:
        result = await rag_service.search_knowledge(
            query=query,
            top_k=3,
            use_cache=False
        )

        results = result.get("results", [])
        print(f"\n检索到 {len(results)} 个结果")

        if results:
            for i, r in enumerate(results, 1):
                print(f"\n结果 {i}:")
                print(f"  数据结构: {r.keys()}")
                # 兼容不同的字段名
                score = r.get('score') or r.get('distance') or r.get('similarity', 0)
                print(f"  相似度: {score:.3f}")
                print(f"  内容: {r.get('content', '')[:100]}...")
        else:
            print("\n未检索到任何结果")
            print("系统应该继续生成答案（基于通用知识）")

    except Exception as e:
        print(f"\n检索失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_no_results())
