"""
文档相关Pydantic模型
"""
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import datetime


class DocumentUpload(BaseModel):
    """文档上传"""
    title: str = Field(..., max_length=255)


class WebpageUpload(BaseModel):
    """网页上传"""
    url: str = Field(..., max_length=500)
    title: Optional[str] = Field(None, max_length=255)


class DocumentResponse(BaseModel):
    """文档响应"""
    id: int
    user_id: int
    title: str
    file_type: str
    file_path: Optional[str]
    url: Optional[str]
    file_hash: Optional[str]
    file_size: Optional[int]
    chunk_count: int
    status: str
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    total: int
    items: list[DocumentResponse]


class DocumentStatusResponse(BaseModel):
    """文档处理状态响应"""
    id: int
    status: str
    chunk_count: int
    error_message: Optional[str]
