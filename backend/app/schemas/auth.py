"""
认证相关Pydantic模型
"""
from pydantic import BaseModel
from typing import Optional


class TokenData(BaseModel):
    """Token数据"""
    user_id: Optional[int] = None
    username: Optional[str] = None
