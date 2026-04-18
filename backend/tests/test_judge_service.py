"""
测试评判服务
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.judge_service import JudgeService


async def test_retrieval_quality_judge():
    """测试检索质量评判器"""
    print("\n" + "="*60)
    print("测试1: 检索质量评判器")
    print("="*60)

    judge_service = JudgeService()

    # 测试用例1: 高相关性
    print("\n【用例1】高相关性文档")
    query = "什么是机器学习？"
    docs = [
        {
            "content": "机器学习是人工智能的一个分支，它使计算机能够在没有明确编程的情况下学习。机器学习算法通过分析数据来识别模式，并根据这些模式做出决策。",
            "score": 0.95
        },
        {
            "content": "机器学习的主要类型包括监督学习、无监督学习和强化学习。监督学习使用标记的数据进行训练，无监督学习从未标记的数据中发现模式。",
            "score": 0.88
        }
    ]

    result = await judge_service.judge_retrieval_quality(query, docs)
    print(f"评分: {result.get('score')}/10")
    print(f"是否相关: {result.get('is_relevant')}")
    print(f"是否通过: {result.get('passed')}")
    print(f"理由: {result.get('reason')}")

    # 测试用例2: 低相关性
    print("\n【用例2】低相关性文档")
    query = "什么是机器学习？"
    docs = [
        {
            "content": "Python是一种高级编程语言，以其简洁的语法和强大的功能而闻名。它广泛应用于Web开发、数据分析等领域。",
            "score": 0.45
        }
    ]

    result = await judge_service.judge_retrieval_quality(query, docs)
    print(f"评分: {result.get('score')}/10")
    print(f"是否相关: {result.get('is_relevant')}")
    print(f"是否通过: {result.get('passed')}")
    print(f"理由: {result.get('reason')}")


async def test_consistency_checker():
    """测试一致性检查器"""
    print("\n" + "="*60)
    print("测试2: 一致性检查器")
    print("="*60)

    judge_service = JudgeService()

    # 测试用例1: 无矛盾
    print("\n【用例1】无矛盾的文档")
    docs = [
        {
            "content": "Python 3.12于2023年10月发布，是Python的最新稳定版本。",
            "score": 0.95
        },
        {
            "content": "Python 3.12引入了多项性能改进和新特性，包括更好的错误消息和类型提示支持。",
            "score": 0.88
        }
    ]

    result = await judge_service.check_consistency(docs)
    print(f"是否存在矛盾: {result.get('has_conflict')}")
    print(f"矛盾列表: {result.get('conflicts')}")
    print(f"总结: {result.get('summary')}")

    # 测试用例2: 有矛盾
    print("\n【用例2】有矛盾的文档")
    docs = [
        {
            "content": "Python 3.12于2023年10月发布。",
            "score": 0.95
        },
        {
            "content": "Python 3.12于2024年1月发布。",
            "score": 0.88
        }
    ]

    result = await judge_service.check_consistency(docs)
    print(f"是否存在矛盾: {result.get('has_conflict')}")
    print(f"矛盾列表: {result.get('conflicts')}")
    print(f"总结: {result.get('summary')}")


async def test_answer_quality_judge():
    """测试答案质量评判器"""
    print("\n" + "="*60)
    print("测试3: 答案质量评判器")
    print("="*60)

    judge_service = JudgeService()

    # 测试用例1: 高质量答案
    print("\n【用例1】高质量答案")
    query = "什么是机器学习？"
    context = """
    机器学习是人工智能的一个分支，它使计算机能够在没有明确编程的情况下学习。
    机器学习算法通过分析数据来识别模式，并根据这些模式做出决策。
    """
    answer = """
    机器学习是人工智能的一个重要分支。它的核心思想是让计算机通过数据学习，
    而不需要人工编写明确的规则。机器学习算法会分析大量数据，从中识别出模式和规律，
    然后利用这些模式来做出预测或决策。这种方法在图像识别、自然语言处理等领域有广泛应用。
    """

    result = await judge_service.judge_answer_quality(query, context, answer)
    print(f"评分: {result.get('score')}/10")
    print(f"是否可接受: {result.get('is_acceptable')}")
    print(f"是否通过: {result.get('passed')}")
    print(f"理由: {result.get('reason')}")
    print(f"问题列表: {result.get('issues')}")

    # 测试用例2: 低质量答案（偏离主题）
    print("\n【用例2】低质量答案（偏离主题）")
    query = "什么是机器学习？"
    context = """
    机器学习是人工智能的一个分支，它使计算机能够在没有明确编程的情况下学习。
    """
    answer = """
    Python是一种非常流行的编程语言，它有简洁的语法和丰富的库。
    很多人用Python来做数据分析和Web开发。
    """

    result = await judge_service.judge_answer_quality(query, context, answer)
    print(f"评分: {result.get('score')}/10")
    print(f"是否可接受: {result.get('is_acceptable')}")
    print(f"是否通过: {result.get('passed')}")
    print(f"理由: {result.get('reason')}")
    print(f"问题列表: {result.get('issues')}")


async def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("开始测试评判服务")
    print("="*60)

    try:
        # 测试1: 检索质量评判
        await test_retrieval_quality_judge()

        # 测试2: 一致性检查
        await test_consistency_checker()

        # 测试3: 答案质量评判
        await test_answer_quality_judge()

        print("\n" + "="*60)
        print("[SUCCESS] All tests completed")
        print("="*60)

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
