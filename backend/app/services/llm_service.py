"""
LLM服务
封装OpenAI API和Ollama调用
"""
import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
import ollama
from app.config.settings import settings
from app.core.llm_balancer import get_llm_balancer, LLMBalancer

logger = logging.getLogger(__name__)


class LLMService:
    """LLM服务"""

    def __init__(self):
        # OpenAI客户端（用于qwen3-max）
        self.openai_client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL
        )

        # Ollama客户端（用于deepseek-r1:7b）
        self.ollama_client = ollama.AsyncClient()

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        聊天补全
        自动使用负载均衡器选择模型（除非指定model参数）

        Args:
            model: 指定模型名称，如果为None则使用负载均衡器
        """
        balancer = await get_llm_balancer()
        current_model = model if model else await balancer.get_current_model()

        try:
            # 判断使用哪个API
            # qwen 系列模型使用 OpenAI API
            if current_model.startswith("qwen") or current_model == LLMBalancer.PRIMARY_MODEL:
                # 使用主模型（qwen3-max）或其他qwen系列模型
                response = await self._call_openai(
                    messages=messages,
                    model=current_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=stream
                )
            else:
                # 使用备用模型（deepseek-r1:7b）或其他ollama模型
                response = await self._call_ollama(
                    messages=messages,
                    model=current_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=stream
                )

            # 记录成功（仅当未指定模型时）
            if not model:
                await balancer.record_success(current_model)
            return response

        except Exception as e:
            logger.error(f"LLM调用失败 (模型: {current_model}): {e}")

            # 如果指定了模型，直接抛出异常，不进行切换
            if model:
                raise

            # 记录失败
            switched = await balancer.record_failure(current_model)

            if switched:
                # 已切换模型，重试一次
                logger.info("模型已切换，重试调用")
                return await self.chat_completion(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=stream,
                    model=None  # 重试时不指定模型
                )
            else:
                # 未切换，直接抛出异常
                raise

    async def _call_openai(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        stream: bool
    ) -> Dict[str, Any]:
        """调用OpenAI API"""
        try:
            response = await self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream
            )

            if stream:
                return {"stream": response}
            else:
                return {
                    "content": response.choices[0].message.content,
                    "model": response.model,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    },
                    "finish_reason": response.choices[0].finish_reason
                }

        except Exception as e:
            logger.error(f"OpenAI API调用失败: {e}")
            raise

    async def _call_ollama(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        stream: bool
    ) -> Dict[str, Any]:
        """调用Ollama API"""
        try:
            response = await self.ollama_client.chat(
                model=model,
                messages=messages,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens
                },
                stream=stream
            )

            if stream:
                return {"stream": response}
            else:
                return {
                    "content": response["message"]["content"],
                    "model": response["model"],
                    "usage": {
                        "prompt_tokens": response.get("prompt_eval_count", 0),
                        "completion_tokens": response.get("eval_count", 0),
                        "total_tokens": response.get("prompt_eval_count", 0) + response.get("eval_count", 0)
                    },
                    "finish_reason": "stop"
                }

        except Exception as e:
            logger.error(f"Ollama API调用失败: {e}")
            raise

    async def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ):
        """
        流式聊天补全
        自动使用负载均衡器选择模型
        """
        balancer = await get_llm_balancer()
        current_model = await balancer.get_current_model()

        try:
            # 判断使用哪个API
            # qwen 系列模型使用 OpenAI API
            if current_model.startswith("qwen") or current_model == LLMBalancer.PRIMARY_MODEL:
                # 使用主模型（qwen3-max）或其他qwen系列模型流式调用
                async for chunk in self._stream_openai(
                    messages=messages,
                    model=current_model,
                    temperature=temperature,
                    max_tokens=max_tokens
                ):
                    yield chunk
            else:
                # 使用备用模型（deepseek-r1:7b）或其他ollama模型流式调用
                async for chunk in self._stream_ollama(
                    messages=messages,
                    model=current_model,
                    temperature=temperature,
                    max_tokens=max_tokens
                ):
                    yield chunk

            # 记录成功
            await balancer.record_success(current_model)

        except Exception as e:
            logger.error(f"LLM流式调用失败 (模型: {current_model}): {e}")
            await balancer.record_failure(current_model)
            raise

    async def _stream_openai(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int
    ):
        """OpenAI流式调用"""
        try:
            stream = await self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield {
                        "content": chunk.choices[0].delta.content,
                        "model": model
                    }

        except Exception as e:
            logger.error(f"OpenAI流式调用失败: {e}")
            raise

    async def _stream_ollama(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int
    ):
        """Ollama流式调用"""
        try:
            stream = await self.ollama_client.chat(
                model=model,
                messages=messages,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens
                },
                stream=True
            )

            async for chunk in stream:
                if chunk.get("message", {}).get("content"):
                    yield {
                        "content": chunk["message"]["content"],
                        "model": model
                    }

        except Exception as e:
            logger.error(f"Ollama流式调用失败: {e}")
            raise

    async def get_embedding(self, text: str) -> List[float]:
        """
        获取文本向量
        使用OpenAI的embedding模型
        """
        try:
            response = await self.openai_client.embeddings.create(
                model=settings.EMBEDDING_MODEL,
                input=text
            )
            return response.data[0].embedding

        except Exception as e:
            logger.error(f"获取向量失败: {e}")
            raise

    async def test_model(self, model: str) -> bool:
        """
        测试模型是否可用
        """
        try:
            test_messages = [
                {"role": "user", "content": "Hello"}
            ]

            # 判断使用哪个API
            if model.startswith("qwen") or model == LLMBalancer.PRIMARY_MODEL:
                await self._call_openai(
                    messages=test_messages,
                    model=model,
                    temperature=0.7,
                    max_tokens=10,
                    stream=False
                )
            else:
                await self._call_ollama(
                    messages=test_messages,
                    model=model,
                    temperature=0.7,
                    max_tokens=10,
                    stream=False
                )

            return True

        except Exception as e:
            logger.error(f"模型测试失败 ({model}): {e}")
            return False
