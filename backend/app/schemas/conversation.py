"""
对话相关Pydantic模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ConversationCreate(BaseModel):
    """创建会话"""
    title: Optional[str] = Field(None, max_length=255)


class MessageSend(BaseModel):
    """发送消息"""
    session_id: str
    content: str = Field(..., min_length=1)
    use_rag: bool = True


class MessageResponse(BaseModel):
    """消息响应"""
    id: int
    role: str
    content: str
    rag_context: Optional[str]
    model_name: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """会话响应"""
    id: int
    session_id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationDetailResponse(BaseModel):
    """会话详情响应"""
    conversation: ConversationResponse
    messages: List[MessageResponse]


class ChatResponse(BaseModel):
    """聊天响应"""
    message: MessageResponse
    answer: str
