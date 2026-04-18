"""
智能客服对话服务
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.conversation import Conversation, Message
from app.services.rag_service import RAGService
from app.services.llm_service import LLMService
from app.config.database import get_db

logger = logging.getLogger(__name__)


class ChatService:
    """对话服务"""

    MAX_HISTORY_ROUNDS = 5  # 最大历史轮数
    MAX_HISTORY_TOKENS = 4000  # 最大历史tokens

    def __init__(self, db: AsyncSession):
        self.db = db
        self.rag_service = RAGService()
        self.llm_service = LLMService()

    async def create_conversation(self, user_id: int, title: Optional[str] = None) -> Conversation:
        """创建对话会话"""
        if not title:
            title = f"对话 {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        # 生成session_id
        import uuid
        session_id = str(uuid.uuid4())

        conversation = Conversation(
            user_id=user_id,
            session_id=session_id,
            title=title
        )

        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)

        logger.info(f"创建对话会话: {conversation.id}, 用户: {user_id}")
        return conversation

    async def get_conversations(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取用户的对话会话列表"""
        offset = (page - 1) * page_size

        # 查询总数
        count_stmt = select(func.count(Conversation.id)).where(
            Conversation.user_id == user_id
        )
        total = await self.db.scalar(count_stmt)

        # 查询列表
        stmt = select(Conversation).where(
            Conversation.user_id == user_id
        ).order_by(desc(Conversation.updated_at)).offset(offset).limit(page_size)

        result = await self.db.execute(stmt)
        conversations = result.scalars().all()

        # 为每个会话计算消息数量
        conversations_with_count = []
        for conv in conversations:
            msg_count_stmt = select(func.count(Message.id)).where(
                Message.conversation_id == conv.id
            )
            msg_count = await self.db.scalar(msg_count_stmt) or 0

            # 动态添加message_count属性
            conv.message_count = msg_count
            conversations_with_count.append(conv)

        return {
            "items": conversations_with_count,
            "total": total,
            "page": page,
            "page_size": page_size
        }

    async def get_conversation(self, conversation_id: int, user_id: int) -> Optional[Conversation]:
        """获取对话会话详情"""
        stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_conversation(self, conversation_id: int, user_id: int) -> bool:
        """删除对话会话"""
        conversation = await self.get_conversation(conversation_id, user_id)
        if not conversation:
            return False

        await self.db.delete(conversation)
        await self.db.commit()

        logger.info(f"删除对话会话: {conversation_id}")
        return True

    async def get_conversation_history(
        self,
        conversation_id: int,
        limit: int = 10
    ) -> List[Message]:
        """获取对话历史"""
        stmt = select(Message).where(
            Message.conversation_id == conversation_id
        ).order_by(desc(Message.created_at)).limit(limit)

        result = await self.db.execute(stmt)
        messages = result.scalars().all()

        # 反转顺序（从旧到新）
        return list(reversed(messages))

    async def send_message(
        self,
        conversation_id: int,
        user_id: int,
        content: str,
        use_rag: bool = True,
        document_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        发送消息并获取AI回复
        """
        # 验证会话
        conversation = await self.get_conversation(conversation_id, user_id)
        if not conversation:
            raise ValueError("会话不存在")

        # 保存用户消息
        user_message = Message(
            conversation_id=conversation_id,
            role="user",
            content=content
        )
        self.db.add(user_message)

        # 构建对话上下文
        messages = await self._build_chat_context(
            conversation_id=conversation_id,
            user_query=content,
            use_rag=use_rag,
            document_id=document_id
        )

        # 调用LLM
        try:
            response = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )

            # 保存AI回复
            assistant_message = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=response["content"],
                tokens_used=response["usage"]["total_tokens"],
                model_name=response["model"]
            )
            self.db.add(assistant_message)

            # 更新会话的updated_at
            conversation.updated_at = datetime.now()

            await self.db.commit()
            await self.db.refresh(user_message)
            await self.db.refresh(assistant_message)

            logger.info(f"对话完成: 会话={conversation_id}, tokens={response['usage']['total_tokens']}")

            return {
                "user_message": user_message,
                "assistant_message": assistant_message,
                "usage": response["usage"]
            }

        except Exception as e:
            await self.db.rollback()
            logger.error(f"对话失败: {e}")
            raise

    async def _build_chat_context(
        self,
        conversation_id: int,
        user_query: str,
        use_rag: bool = True,
        document_id: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """构建对话上下文"""
        messages = []

        # 系统提示
        system_prompt = "你是一个专业的AI助手，请根据提供的参考资料回答用户问题。"

        # RAG检索
        rag_context = ""
        if use_rag:
            try:
                search_result = await self.rag_service.search_knowledge(
                    query=user_query,
                    top_k=3,
                    document_id=document_id,
                    use_cache=True
                )
                if search_result["results"]:
                    rag_context = self.rag_service.build_rag_context(search_result["results"])
                    system_prompt += f"\n\n参考资料：\n{rag_context}"
            except Exception as e:
                logger.warning(f"RAG检索失败: {e}")

        messages.append({"role": "system", "content": system_prompt})

        # 获取历史对话
        history = await self.get_conversation_history(
            conversation_id=conversation_id,
            limit=self.MAX_HISTORY_ROUNDS * 2
        )

        # 添加历史消息
        for msg in history:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        # 添加当前用户消息
        messages.append({"role": "user", "content": user_query})

        # TODO: 如果历史太长，进行压缩
        # total_tokens = self._estimate_tokens(messages)
        # if total_tokens > self.MAX_HISTORY_TOKENS:
        #     messages = self._compress_history(messages)

        return messages

    def _estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        """估算tokens数量（简单估算：1个字符约等于1.5个token）"""
        total_chars = sum(len(msg["content"]) for msg in messages)
        return int(total_chars * 1.5)

    def _compress_history(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """压缩历史对话（保留系统提示和最近的对话）"""
        if len(messages) <= 3:
            return messages

        # 保留系统提示和最后一条用户消息
        system_msg = messages[0]
        user_msg = messages[-1]

        # 保留最近的几轮对话
        recent_messages = messages[-5:-1] if len(messages) > 5 else messages[1:-1]

        return [system_msg] + recent_messages + [user_msg]

    async def send_message_stream(
        self,
        conversation_id: int,
        user_id: int,
        content: str,
        use_rag: bool = True,
        document_id: Optional[int] = None
    ):
        """
        发送消息并流式获取AI回复
        """
        # 验证会话
        conversation = await self.get_conversation(conversation_id, user_id)
        if not conversation:
            raise ValueError("会话不存在")

        # 保存用户消息
        user_message = Message(
            conversation_id=conversation_id,
            role="user",
            content=content
        )
        self.db.add(user_message)
        await self.db.commit()
        await self.db.refresh(user_message)

        # 发送用户消息
        yield {
            "type": "user_message",
            "data": {
                "id": user_message.id,
                "role": "user",
                "content": content,
                "created_at": user_message.created_at.isoformat()
            }
        }

        # RAG检索
        rag_results = []
        if use_rag:
            try:
                search_result = await self.rag_service.search_knowledge(
                    query=content,
                    top_k=3,
                    document_id=document_id,
                    use_cache=True
                )
                rag_results = search_result.get("results", [])

                # 发送检索到的信息
                if rag_results:
                    yield {
                        "type": "rag_context",
                        "data": {
                            "results": [
                                {
                                    "content": r["content"],
                                    "score": r["score"],
                                    "document_title": r.get("document_title", "未知文档")
                                }
                                for r in rag_results
                            ]
                        }
                    }
            except Exception as e:
                logger.warning(f"RAG检索失败: {e}")

        # 构建对话上下文
        messages = await self._build_chat_context(
            conversation_id=conversation_id,
            user_query=content,
            use_rag=use_rag,
            document_id=document_id
        )

        # 流式调用LLM
        full_content = ""
        try:
            # 检查LLM服务是否支持流式
            if hasattr(self.llm_service, 'chat_completion_stream'):
                async for chunk in self.llm_service.chat_completion_stream(
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2000
                ):
                    full_content += chunk.get("content", "")
                    yield {
                        "type": "assistant_chunk",
                        "data": {
                            "content": chunk.get("content", "")
                        }
                    }
            else:
                # 降级到非流式
                response = await self.llm_service.chat_completion(
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2000
                )
                full_content = response["content"]
                yield {
                    "type": "assistant_chunk",
                    "data": {
                        "content": full_content
                    }
                }

            # 保存AI回复
            assistant_message = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=full_content,
                tokens_used=len(full_content),  # 简单估算
                model_name="gpt-3.5-turbo"
            )
            self.db.add(assistant_message)

            # 更新会话
            conversation.updated_at = datetime.now()
            await self.db.commit()
            await self.db.refresh(assistant_message)

            # 发送完成消息
            yield {
                "type": "assistant_message",
                "data": {
                    "id": assistant_message.id,
                    "role": "assistant",
                    "content": full_content,
                    "tokens": assistant_message.tokens_used,
                    "model": assistant_message.model_name,
                    "created_at": assistant_message.created_at.isoformat()
                }
            }

            logger.info(f"流式对话完成: 会话={conversation_id}")

        except Exception as e:
            await self.db.rollback()
            logger.error(f"流式对话失败: {e}")
            raise
