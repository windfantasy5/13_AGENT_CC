"""
智能客服对话API
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.schemas.chat import (
    ConversationCreate,
    ConversationResponse,
    ConversationDetail,
    MessageSend,
    MessageResponse
)
from app.services.chat_service import ChatService
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.config.database import get_db
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/conversations", response_model=dict)
async def create_conversation(
    request: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    创建对话会话
    """
    try:
        chat_service = ChatService(db)
        conversation = await chat_service.create_conversation(
            user_id=current_user.id,
            title=request.title
        )

        return {
            "code": 200,
            "message": "创建成功",
            "data": {
                "id": conversation.id,
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat()
            }
        }

    except Exception as e:
        logger.error(f"创建对话会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations", response_model=dict)
async def get_conversations(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取对话会话列表
    """
    try:
        chat_service = ChatService(db)
        result = await chat_service.get_conversations(
            user_id=current_user.id,
            page=page,
            page_size=page_size
        )

        conversations = [
            {
                "id": conv.id,
                "title": conv.title,
                "message_count": getattr(conv, 'message_count', 0),
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat()
            }
            for conv in result["items"]
        ]

        return {
            "code": 200,
            "message": "success",
            "data": {
                "items": conversations,
                "total": result["total"],
                "page": result["page"],
                "page_size": result["page_size"]
            }
        }

    except Exception as e:
        logger.error(f"获取对话列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}", response_model=dict)
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取对话会话详情
    """
    try:
        chat_service = ChatService(db)
        conversation = await chat_service.get_conversation(
            conversation_id=conversation_id,
            user_id=current_user.id
        )

        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")

        # 获取消息历史
        messages = await chat_service.get_conversation_history(
            conversation_id=conversation_id,
            limit=50
        )

        # 计算消息数量
        from sqlalchemy import select, func
        from app.models.conversation import Message
        msg_count_stmt = select(func.count(Message.id)).where(
            Message.conversation_id == conversation_id
        )
        msg_count = await db.scalar(msg_count_stmt) or 0

        return {
            "code": 200,
            "message": "success",
            "data": {
                "id": conversation.id,
                "title": conversation.title,
                "message_count": msg_count,
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat(),
                "messages": [
                    {
                        "id": msg.id,
                        "role": msg.role,
                        "content": msg.content,
                        "tokens": msg.tokens_used,
                        "model": msg.model_name,
                        "created_at": msg.created_at.isoformat()
                    }
                    for msg in messages
                ]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取对话详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversations/{conversation_id}", response_model=dict)
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除对话会话
    """
    try:
        chat_service = ChatService(db)
        success = await chat_service.delete_conversation(
            conversation_id=conversation_id,
            user_id=current_user.id
        )

        if not success:
            raise HTTPException(status_code=404, detail="会话不存在")

        return {
            "code": 200,
            "message": "删除成功",
            "data": None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除对话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message", response_model=dict)
async def send_message(
    request: MessageSend,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    发送消息并获取AI回复
    """
    try:
        chat_service = ChatService(db)
        result = await chat_service.send_message(
            conversation_id=request.conversation_id,
            user_id=current_user.id,
            content=request.content,
            use_rag=request.use_rag,
            document_id=request.document_id
        )

        return {
            "code": 200,
            "message": "success",
            "data": {
                "user_message": {
                    "id": result["user_message"].id,
                    "role": result["user_message"].role,
                    "content": result["user_message"].content,
                    "created_at": result["user_message"].created_at.isoformat()
                },
                "assistant_message": {
                    "id": result["assistant_message"].id,
                    "role": result["assistant_message"].role,
                    "content": result["assistant_message"].content,
                    "tokens": result["assistant_message"].tokens_used,
                    "model": result["assistant_message"].model_name,
                    "created_at": result["assistant_message"].created_at.isoformat()
                },
                "usage": result["usage"]
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"发送消息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message/stream")
async def send_message_stream(
    request: MessageSend,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    发送消息并获取AI流式回复
    """
    async def generate():
        try:
            chat_service = ChatService(db)

            # 流式生成响应
            async for chunk in chat_service.send_message_stream(
                conversation_id=request.conversation_id,
                user_id=current_user.id,
                content=request.content,
                use_rag=request.use_rag,
                document_id=request.document_id
            ):
                # 发送SSE格式数据
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

            # 发送结束标记
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"流式发送消息失败: {e}")
            error_data = {
                "type": "error",
                "content": str(e)
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
