"""
配置管理模块
"""
from pydantic_settings import BaseSettings
from typing import List
import os
from pathlib import Path

# 项目根目录：backend/app/config/settings.py -> 向上3级 -> 项目根目录
# 结构: 项目根/backend/app/config/settings.py
_THIS_FILE = Path(__file__).resolve()
# backend目录
_BACKEND_DIR = _THIS_FILE.parent.parent.parent
# 项目根目录（backend的父目录）
PROJECT_ROOT = _BACKEND_DIR.parent


class Settings(BaseSettings):
    """应用配置"""

    # 数据库配置
    ASYNC_DATABASE_URL: str = "mysql+aiomysql://root:123456@localhost:3306/agent_app?charset=utf8"
    SYNC_DATABASE_URL: str = "mysql+pymysql://root:123456@localhost:3306/agent_app?charset=utf8"

    # Redis配置
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT配置
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 7

    # LLM配置
    DASHSCOPE_API_KEY: str = ""
    LLM_API_KEY: str = ""  # OpenAI兼容API密钥
    LLM_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"  # OpenAI兼容端点
    QWEN_MODEL_NAME: str = "qwen3-max"
    OLLAMA_MODEL_NAME: str = "deepseek-r1:7b"
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # 向量模型配置
    EMBEDDING_MODEL_NAME: str = "text-embedding-v4"
    EMBEDDING_MODEL: str = "text-embedding-v4"  # 向量模型别名

    # 文件上传配置
    MAX_UPLOAD_SIZE: int = 52428800  # 50MB
    # 使用相对路径配置，运行时转为绝对路径
    UPLOAD_DIR: str = "data/uploads"

    # Chroma配置（相对于项目根目录的路径，运行时转为绝对路径）
    CHROMA_DB_PATH: str = "chroma_db"

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # CORS配置
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        """获取CORS origins列表"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def chroma_db_abs_path(self) -> str:
        """获取ChromaDB的绝对路径（基于项目根目录）"""
        path = Path(self.CHROMA_DB_PATH)
        if path.is_absolute():
            return str(path)
        return str(PROJECT_ROOT / self.CHROMA_DB_PATH)

    @property
    def upload_dir_abs_path(self) -> str:
        """获取上传目录的绝对路径（基于项目根目录）"""
        path = Path(self.UPLOAD_DIR)
        if path.is_absolute():
            return str(path)
        return str(PROJECT_ROOT / self.UPLOAD_DIR)

    class Config:
        env_file = ".env"
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 从环境变量获取API密钥
        if not self.DASHSCOPE_API_KEY:
            self.DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
        # LLM_API_KEY默认使用DASHSCOPE_API_KEY
        if not self.LLM_API_KEY:
            self.LLM_API_KEY = self.DASHSCOPE_API_KEY or os.getenv("LLM_API_KEY", "")


settings = Settings()

# 导出项目根目录供其他模块使用
__all__ = ["settings", "PROJECT_ROOT"]

