"""
Judge Service - Quality assessment service for RAG system
"""
import json
import logging
from typing import List, Dict, Any, Optional
from app.services.llm_service import LLMService
from app.prompts.judge_prompts import (
    RETRIEVAL_QUALITY_PROMPT,
    CONSISTENCY_CHECKER_PROMPT,
    ANSWER_QUALITY_PROMPT
)

logger = logging.getLogger(__name__)


class JudgeConfig:
    """评判配置"""
    JUDGE_MODEL = "qwen-turbo"  # 评判模型（轻量快速）- 通过OpenAI API调用
    GENERATION_MODEL = "qwen3-max"  # 生成模型（高质量）
    RETRIEVAL_THRESHOLD = 6  # 检索质量阈值
    ANSWER_THRESHOLD = 7  # 答案质量阈值
    MAX_RETRIES = 2  # 最大重试次数
    JUDGE_TEMPERATURE = 0.1  # 评判温度（低温度保证稳定性）
    JUDGE_MAX_TOKENS = 1000  # 评判最大tokens
    USE_OPENAI_API = True  # 使用OpenAI API调用评判模型


class JudgeService:
    """评判服务"""

    def __init__(self):
        self.llm_service = LLMService()
        self.config = JudgeConfig()

    async def judge_retrieval_quality(
        self,
        query: str,
        retrieved_docs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        评判检索质量

        Args:
            query: 用户问题
            retrieved_docs: 检索到的文档列表

        Returns:
            {
                "score": int,  # 0-10评分
                "reason": str,  # 评判理由
                "is_relevant": bool,  # 是否相关
                "passed": bool  # 是否通过阈值
            }
        """
        if not retrieved_docs:
            return {
                "score": 0,
                "reason": "未检索到任何文档",
                "is_relevant": False,
                "passed": False
            }

        # 构建参考资料文本
        context = self._build_context_text(retrieved_docs)

        # 构建评判提示
        prompt = RETRIEVAL_QUALITY_PROMPT.format(
            query=query,
            context=context
        )

        try:
            # 调用评判模型
            response = await self.llm_service.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=self.config.JUDGE_TEMPERATURE,
                max_tokens=self.config.JUDGE_MAX_TOKENS,
                model=self.config.JUDGE_MODEL
            )

            # 解析JSON结果
            result = self._parse_json_response(response["content"])

            # 添加是否通过阈值的判断
            result["passed"] = result.get("score", 0) >= self.config.RETRIEVAL_THRESHOLD

            logger.info(f"检索质量评判: score={result.get('score')}, passed={result['passed']}")
            return result

        except Exception as e:
            logger.error(f"检索质量评判失败: {e}")
            # 返回默认通过，避免阻塞流程
            return {
                "score": 6,
                "reason": f"评判失败: {str(e)}",
                "is_relevant": True,
                "passed": True
            }

    async def check_consistency(
        self,
        retrieved_docs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        检查文档一致性

        Args:
            retrieved_docs: 检索到的文档列表

        Returns:
            {
                "has_conflict": bool,  # 是否存在矛盾
                "conflicts": List[Dict],  # 矛盾列表
                "summary": str  # 总体评价
            }
        """
        if len(retrieved_docs) < 2:
            return {
                "has_conflict": False,
                "conflicts": [],
                "summary": "文档数量不足，无需检查一致性"
            }

        # 构建文档列表文本
        contexts = self._build_contexts_list(retrieved_docs)

        # 构建检查提示
        prompt = CONSISTENCY_CHECKER_PROMPT.format(contexts=contexts)

        try:
            # 调用评判模型
            response = await self.llm_service.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=self.config.JUDGE_TEMPERATURE,
                max_tokens=self.config.JUDGE_MAX_TOKENS,
                model=self.config.JUDGE_MODEL
            )

            # 解析JSON结果
            result = self._parse_json_response(response["content"])

            logger.info(f"一致性检查: has_conflict={result.get('has_conflict')}")
            return result

        except Exception as e:
            logger.error(f"一致性检查失败: {e}")
            return {
                "has_conflict": False,
                "conflicts": [],
                "summary": f"检查失败: {str(e)}"
            }

    async def judge_answer_quality(
        self,
        query: str,
        context: str,
        answer: str
    ) -> Dict[str, Any]:
        """
        评判答案质量

        Args:
            query: 用户问题
            context: 参考资料
            answer: AI生成的答案

        Returns:
            {
                "score": int,  # 0-10评分
                "reason": str,  # 评判理由
                "is_acceptable": bool,  # 是否可接受
                "issues": List[str],  # 问题列表
                "passed": bool  # 是否通过阈值
            }
        """
        # 构建评判提示
        prompt = ANSWER_QUALITY_PROMPT.format(
            query=query,
            context=context,
            answer=answer
        )

        try:
            # 调用评判模型
            response = await self.llm_service.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=self.config.JUDGE_TEMPERATURE,
                max_tokens=self.config.JUDGE_MAX_TOKENS,
                model=self.config.JUDGE_MODEL
            )

            # 解析JSON结果
            result = self._parse_json_response(response["content"])

            # 添加是否通过阈值的判断
            result["passed"] = result.get("score", 0) >= self.config.ANSWER_THRESHOLD

            logger.info(f"答案质量评判: score={result.get('score')}, passed={result['passed']}")
            return result

        except Exception as e:
            logger.error(f"答案质量评判失败: {e}")
            # 返回默认通过，避免阻塞流程
            return {
                "score": 7,
                "reason": f"评判失败: {str(e)}",
                "is_acceptable": True,
                "issues": [],
                "passed": True
            }

    def _build_context_text(self, docs: List[Dict[str, Any]]) -> str:
        """构建参考资料文本"""
        context_parts = []
        for i, doc in enumerate(docs, 1):
            content = doc.get("content", "")
            score = doc.get("score", 0)
            context_parts.append(f"[文档{i}] (相似度: {score:.3f})\n{content}")
        return "\n\n".join(context_parts)

    def _build_contexts_list(self, docs: List[Dict[str, Any]]) -> str:
        """构建文档列表文本"""
        contexts_parts = []
        for i, doc in enumerate(docs, 1):
            content = doc.get("content", "")
            contexts_parts.append(f"资料{i}：\n{content}")
        return "\n\n---\n\n".join(contexts_parts)

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """解析JSON响应"""
        try:
            # 尝试直接解析
            return json.loads(response)
        except json.JSONDecodeError:
            # 尝试提取JSON部分
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass

            # 解析失败，返回默认结构
            logger.warning(f"JSON解析失败，原始响应: {response}")
            return {
                "error": "JSON解析失败",
                "raw_response": response
            }
