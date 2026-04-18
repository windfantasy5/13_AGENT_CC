"""
提示词管理API
支持读取和修改对话系统的提示词模板
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from pathlib import Path
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.response import success_response, error_response
from app.config.settings import PROJECT_ROOT
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# 提示词文件路径（固定使用项目内的文件）
PROMPTS_DIR = PROJECT_ROOT / "backend" / "app" / "prompts"
RAG_PROMPT_FILE = PROMPTS_DIR / "rag_summarize.txt"


def _ensure_prompts_dir():
    """确保提示词目录存在"""
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)


def _read_prompt(file_path: Path) -> str:
    """读取提示词文件"""
    if file_path.exists():
        return file_path.read_text(encoding="utf-8")
    return ""


def _write_prompt(file_path: Path, content: str):
    """写入提示词文件"""
    _ensure_prompts_dir()
    file_path.write_text(content, encoding="utf-8")


class PromptUpdate(BaseModel):
    content: str


@router.get("/rag", summary="获取RAG问答提示词")
async def get_rag_prompt(
    current_user: User = Depends(get_current_user)
):
    """获取RAG问答系统提示词"""
    try:
        content = _read_prompt(RAG_PROMPT_FILE)
        return success_response(
            data={
                "content": content,
                "file_path": str(RAG_PROMPT_FILE),
                "exists": RAG_PROMPT_FILE.exists()
            },
            message="获取提示词成功"
        )
    except Exception as e:
        logger.error(f"读取提示词失败: {e}")
        return error_response(code=500, message=str(e))


@router.put("/rag", summary="更新RAG问答提示词")
async def update_rag_prompt(
    body: PromptUpdate,
    current_user: User = Depends(get_current_user)
):
    """更新RAG问答系统提示词"""
    try:
        if not body.content.strip():
            return error_response(code=400, message="提示词内容不能为空")
        _write_prompt(RAG_PROMPT_FILE, body.content)
        logger.info(f"用户 {current_user.username} 更新了RAG提示词")
        return success_response(message="提示词更新成功")
    except Exception as e:
        logger.error(f"保存提示词失败: {e}")
        return error_response(code=500, message=str(e))


@router.post("/rag/reset", summary="重置RAG提示词为默认值")
async def reset_rag_prompt(
    current_user: User = Depends(get_current_user)
):
    """重置RAG问答提示词为系统默认值"""
    default_content = """你是专注于"基于参考资料总结"的AI助手，需结合用户提问和向量检索到的参考资料，生成简洁准确的概括回答。

### 输入信息
1. 用户提问：{input}
2. 参考资料(在下一个###之前内容均为参考资料)：{context}

### 严格遵守以下约束（违反将导致回答无效）
1. 内容合规：禁止包含违法、侵权、攻击性信息；
2. 事实准确：回答必须完全基于参考资料中的信息，不编造、不添加未提及的内容，不做主观推断；
3. 语言要求：仅用中文回答，语气客观、简洁，不冗余；
4. 聚焦提问：严格围绕用户原始提问总结，不扩充问题范围、不额外追问、不构造新query；
5. 格式要求：仅输出概括内容本身，以纯文本字符串形式呈现，不封装为字典、列表、JSON等任何结构，不附带额外说明。"""
    try:
        _write_prompt(RAG_PROMPT_FILE, default_content)
        return success_response(
            data={"content": default_content},
            message="提示词已重置为默认值"
        )
    except Exception as e:
        logger.error(f"重置提示词失败: {e}")
        return error_response(code=500, message=str(e))
