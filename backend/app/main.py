"""
FastAPI主应用入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.api.v1 import auth, user, document, knowledge, llm, chat, prompts

# 创建FastAPI应用
app = FastAPI(
    title="RAG+AGENT企业知识库系统",
    description="企业知识库和智能客服系统API",
    version="1.0.0",
    debug=settings.DEBUG
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(user.router, prefix="/api/v1/users", tags=["用户"])
app.include_router(document.router, prefix="/api/v1/documents", tags=["文档管理"])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["知识库检索"])
app.include_router(llm.router, prefix="/api/v1/llm", tags=["LLM管理"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["智能对话"])
app.include_router(prompts.router, prefix="/api/v1/prompts", tags=["提示词管理"])


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "RAG+AGENT企业知识库系统API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
