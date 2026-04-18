"""
统一响应格式
"""
from pydantic import BaseModel
from typing import Any, Optional
from datetime import datetime


class ResponseModel(BaseModel):
    """统一响应模型"""
    code: int = 200
    message: str = "success"
    data: Optional[Any] = None
    timestamp: datetime = datetime.now()

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


def success_response(data: Any = None, message: str = "success") -> ResponseModel:
    """成功响应"""
    return ResponseModel(code=200, message=message, data=data)


def error_response(code: int = 400, message: str = "error", data: Any = None) -> ResponseModel:
    """错误响应"""
    return ResponseModel(code=code, message=message, data=data)
