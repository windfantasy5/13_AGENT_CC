"""
配置管理模块
"""
from pydantic_settings import BaseSettings
from typing import List
import os


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
    UPLOAD_DIR: str = "./uploads"

    # Chroma配置
    CHROMA_DB_PATH: str = "./chroma_db"

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

