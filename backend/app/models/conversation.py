"""
对话相关数据模型
"""
from sqlalchemy import Column, Integer, String, Text, Enum, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.config.database import Base


class Conversation(Base):
    """对话会话表"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")



class Message(Base):
    """对话消息表"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(Enum('user', 'assistant', 'system'), nullable=False)
    content = Column(Text, nullable=False)
    rag_context = Column(Text)
    model_name = Column(String(50))
    tokens_used = Column(Integer)
    created_at = Column(DateTime, server_default=func.now(), index=True)

    # 关系
    conversation = relationship("Conversation", back_populates="messages")


class SystemLog(Base):
    """系统日志表"""
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    action = Column(String(100), nullable=False, index=True)
    module = Column(String(50), index=True)
    resource = Column(String(100))
    question = Column(Text)
    answer = Column(Text)
    rag_context = Column(Text)
    details = Column(Text)
    ip_address = Column(String(50))
    created_at = Column(DateTime, server_default=func.now(), index=True)
