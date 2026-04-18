"""
文档相关数据模型
"""
from sqlalchemy import Column, Integer, String, Text, Enum, BigInteger, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.config.database import Base


class Document(Base):
    """文档记录表"""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    file_type = Column(Enum('txt', 'word', 'pdf', 'webpage'), nullable=False)
    file_path = Column(String(500))
    url = Column(String(500))
    file_hash = Column(String(64), unique=True, index=True)
    file_size = Column(BigInteger)
    chunk_count = Column(Integer, default=0)
    status = Column(Enum('pending', 'processing', 'completed', 'failed'), default='pending', index=True)
    error_message = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")



class DocumentChunk(Base):
    """文档分段表"""
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    char_count = Column(Integer)
    vector_id = Column(String(100), index=True)
    created_at = Column(DateTime, server_default=func.now())

    # 关系
    document = relationship("Document", back_populates="chunks")
