"""
对话相关Schema
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ConversationCreate(BaseModel):
    """创建对话会话"""
    title: Optional[str] = Field(None, description="会话标题", max_length=255)


class MessageSend(BaseModel):
    """发送消息"""
    conversation_id: int = Field(..., description="会话ID")
    content: str = Field(..., description="消息内容", min_length=1, max_length=2000)
    use_rag: bool = Field(True, description="是否使用RAG检索")
    document_id: Optional[int] = Field(None, description="指定文档ID")


class MessageResponse(BaseModel):
    """消息响应"""
    id: int
    conversation_id: int
    role: str
    content: str
    tokens: Optional[int]
    model: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """会话响应"""
    id: int
    user_id: int
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationDetail(BaseModel):
    """会话详情"""
    id: int
    user_id: int
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse]

    class Config:
        from_attributes = True
