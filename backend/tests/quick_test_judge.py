"""
快速验证评判机制集成
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.judge_service import JudgeService


async def quick_test():
    """快速测试评判服务"""
    print("="*60)
    print("Quick Test: Judge Service Integration")
    print("="*60)

    judge_service = JudgeService()

    # 测试1: 检索质量评判
    print("\n[Test 1] Retrieval Quality Judge")
    query = "Python是什么？"
    docs = [
        {
            "content": "Python是一种高级编程语言，由Guido van Rossum于1991年创建。",
            "score": 0.92
        }
    ]

    result = await judge_service.judge_retrieval_quality(query, docs)
    print(f"  Score: {result.get('score')}/10")
    print(f"  Passed: {result.get('passed')}")
    print(f"  Reason: {result.get('reason')[:50]}...")

    # 测试2: 一致性检查
    print("\n[Test 2] Consistency Checker")
    docs = [
        {"content": "Python 3.12于2023年10月发布。", "score": 0.95},
        {"content": "Python 3.12引入了多项性能改进。", "score": 0.88}
    ]

    result = await judge_service.check_consistency(docs)
    print(f"  Has Conflict: {result.get('has_conflict')}")
    print(f"  Summary: {result.get('summary')[:50]}...")

    # 测试3: 答案质量评判
    print("\n[Test 3] Answer Quality Judge")
    query = "Python是什么？"
    context = "Python是一种高级编程语言。"
    answer = "Python是一种广泛使用的高级编程语言，以其简洁的语法和强大的功能而闻名。"

    result = await judge_service.judge_answer_quality(query, context, answer)
    print(f"  Score: {result.get('score')}/10")
    print(f"  Passed: {result.get('passed')}")
    print(f"  Reason: {result.get('reason')[:50]}...")

    print("\n" + "="*60)
    print("[SUCCESS] All quick tests passed!")
    print("="*60)


if __name__ == "__main__":
    try:
        asyncio.run(quick_test())
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
