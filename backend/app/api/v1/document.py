"""
文档管理API
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, delete
from app.config.database import get_db
from app.schemas.document import (
    DocumentResponse, DocumentListResponse, DocumentStatusResponse,
    WebpageUpload
)
from app.schemas.response import ResponseModel, success_response, error_response
from app.models.user import User
from app.models.document import Document, DocumentChunk
from app.models.conversation import SystemLog
from app.api.deps import get_current_user, get_client_ip
from app.services.document_service import DocumentService
from typing import Optional
import logging
import shutil
from pathlib import Path
from app.config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter()
document_service = DocumentService()


@router.post("/preview-upload", response_model=ResponseModel)
async def preview_upload_document(
    file: UploadFile = File(...),
    max_chunk_size: int = Form(500),
    min_chunk_size: int = Form(50),
    overlap_size: int = Form(50),
    current_user: User = Depends(get_current_user)
):
    """预览上传文档的分段"""
    try:
        # 读取文件内容
        file_content = await file.read()

        # 提取文本
        text = await document_service.extract_text_from_bytes(
            file_content=file_content,
            filename=file.filename
        )

        # 预览分段
        params = {
            "max_chunk_size": max_chunk_size,
            "min_chunk_size": min_chunk_size,
            "overlap_size": overlap_size
        }

        preview_result = document_service.preview_chunks(text, params)

        return success_response(
            data={
                **preview_result,
                "filename": file.filename,
                "file_size": len(file_content)
            },
            message="文档预览成功"
        )

    except Exception as e:
        logger.error(f"文档预览失败: {e}")
        return error_response(code=400, message=str(e))


@router.post("/upload", response_model=ResponseModel)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    max_chunk_size: int = Form(500),
    min_chunk_size: int = Form(50),
    overlap_size: int = Form(50),
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """上传文档并保存到向量数据库"""
    try:
        # 读取文件内容
        file_content = await file.read()

        # 使用文件名作为标题(如果未提供)
        doc_title = title or file.filename

        # 处理文件上传
        document = await document_service.process_file_upload(
            file_content=file_content,
            filename=file.filename,
            title=doc_title,
            user_id=current_user.id,
            db=db
        )

        # 提取文本
        text = await document_service.extract_text_from_file(document)

        # 保存分段到向量数据库
        params = {
            "max_chunk_size": max_chunk_size,
            "min_chunk_size": min_chunk_size,
            "overlap_size": overlap_size
        }
        chunk_count = await document_service.save_chunks(document.id, text, params, db)

        # 更新文档状态
        document.status = 'completed'
        document.chunk_count = chunk_count
        await db.commit()
        await db.refresh(document)

        # 记录日志
        log = SystemLog(
            user_id=current_user.id,
            action="upload_document",
            module="document_upload",
            resource=document.title,
            details=f"上传文档: {document.title}, 类型: {document.file_type}, 分段数: {chunk_count}",
            ip_address=get_client_ip(request)
        )
        db.add(log)
        await db.commit()

        return success_response(
            data=DocumentResponse.from_orm(document).dict(),
            message="文档上传成功"
        )

    except Exception as e:
        logger.error(f"文档上传失败: {e}")
        return error_response(code=400, message=str(e))


@router.post("/url/preview", response_model=ResponseModel)
async def preview_webpage(
    webpage_data: WebpageUpload,
    current_user: User = Depends(get_current_user)
):
    """预览网页内容（清洗后的Markdown）"""
    try:
        # 抓取并清洗网页
        web_data = await document_service.extract_text_from_url(webpage_data.url)

        return success_response(
            data={
                "title": web_data["title"],
                "url": webpage_data.url,
                "markdown": web_data.get("markdown", ""),
                "content_length": len(web_data["content"])
            },
            message="网页预览成功"
        )
    except Exception as e:
        logger.error(f"网页预览失败: {e}")
        return error_response(code=400, message=str(e))


@router.post("/url", response_model=ResponseModel)
async def add_webpage(
    url: str = Form(...),
    title: Optional[str] = Form(None),
    max_chunk_size: int = Form(500),
    min_chunk_size: int = Form(50),
    overlap_size: int = Form(50),
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """添加网页URL并保存到向量数据库"""
    try:
        # 计算URL哈希
        import hashlib
        url_hash = hashlib.sha256(url.encode()).hexdigest()

        # 检查是否已存在
        result = await db.execute(
            select(Document).where(Document.file_hash == url_hash)
        )
        existing_doc = result.scalar_one_or_none()
        if existing_doc:
            return error_response(code=400, message="该网页已添加")

        # 抓取网页内容
        web_data = await document_service.extract_text_from_url(url)

        # 创建文档记录
        document = Document(
            user_id=current_user.id,
            title=title or web_data["title"],
            file_type='webpage',
            url=url,
            file_hash=url_hash,
            status='pending'
        )
        db.add(document)
        await db.commit()
        await db.refresh(document)

        # 保存分段到向量数据库
        params = {
            "max_chunk_size": max_chunk_size,
            "min_chunk_size": min_chunk_size,
            "overlap_size": overlap_size
        }
        chunk_count = await document_service.save_chunks(
            document.id,
            web_data["content"],  # 使用纯文本内容进行向量化
            params,
            db
        )

        # 更新文档状态
        document.status = 'completed'
        document.chunk_count = chunk_count
        await db.commit()
        await db.refresh(document)

        # 记录日志
        log = SystemLog(
            user_id=current_user.id,
            action="add_webpage",
            module="document_upload",
            resource=document.title,
            details=f"添加网页: {url}, 分段数: {chunk_count}",
            ip_address=get_client_ip(request)
        )
        db.add(log)
        await db.commit()

        return success_response(
            data=DocumentResponse.from_orm(document).dict(),
            message="网页添加成功"
        )

    except Exception as e:
        logger.error(f"添加网页失败: {e}")
        return error_response(code=400, message=str(e))


@router.get("", response_model=ResponseModel)
async def get_documents(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取文档列表"""
    try:
        # 查询总数
        count_result = await db.execute(
            select(Document).where(Document.user_id == current_user.id)
        )
        total = len(count_result.scalars().all())

        # 分页查询
        offset = (page - 1) * page_size
        result = await db.execute(
            select(Document)
            .where(Document.user_id == current_user.id)
            .order_by(desc(Document.created_at))
            .offset(offset)
            .limit(page_size)
        )
        documents = result.scalars().all()

        return success_response(
            data={
                "total": total,
                "items": [DocumentResponse.from_orm(doc).dict() for doc in documents],
                "page": page,
                "page_size": page_size
            }
        )

    except Exception as e:
        logger.error(f"获取文档列表失败: {e}")
        return error_response(code=400, message=str(e))


@router.get("/{doc_id}", response_model=ResponseModel)
async def get_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取文档详情"""
    try:
        result = await db.execute(
            select(Document).where(
                Document.id == doc_id,
                Document.user_id == current_user.id
            )
        )
        document = result.scalar_one_or_none()

        if not document:
            return error_response(code=404, message="文档不存在")

        return success_response(data=DocumentResponse.from_orm(document).dict())

    except Exception as e:
        logger.error(f"获取文档详情失败: {e}")
        return error_response(code=400, message=str(e))


@router.delete("/{doc_id}", response_model=ResponseModel)
async def delete_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除文档"""
    try:
        result = await db.execute(
            select(Document).where(
                Document.id == doc_id,
                Document.user_id == current_user.id
            )
        )
        document = result.scalar_one_or_none()

        if not document:
            return error_response(code=404, message="文档不存在")

        await db.delete(document)
        await db.commit()

        return success_response(message="文档删除成功")

    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        return error_response(code=400, message=str(e))


@router.get("/status/{doc_id}", response_model=ResponseModel)
async def get_document_status(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取文档处理状态"""
    try:
        result = await db.execute(
            select(Document).where(
                Document.id == doc_id,
                Document.user_id == current_user.id
            )
        )
        document = result.scalar_one_or_none()

        if not document:
            return error_response(code=404, message="文档不存在")

        status_data = DocumentStatusResponse(
            id=document.id,
            status=document.status,
            chunk_count=document.chunk_count,
            error_message=document.error_message
        )

        return success_response(data=status_data.dict())

    except Exception as e:
        logger.error(f"获取文档状态失败: {e}")
        return error_response(code=400, message=str(e))


@router.post("/{doc_id}/preview", response_model=ResponseModel)
async def preview_document_chunks(
    doc_id: int,
    params: Optional[dict] = None,
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """预览文档分段"""
    try:
        # 获取文档
        result = await db.execute(
            select(Document).where(
                Document.id == doc_id,
                Document.user_id == current_user.id
            )
        )
        document = result.scalar_one_or_none()

        if not document:
            return error_response(code=404, message="文档不存在")

        # 提取文本
        if document.file_type == 'webpage':
            web_data = await document_service.extract_text_from_url(document.url)
            text = web_data["content"]
        else:
            text = await document_service.extract_text_from_file(document)

        # 预览分段
        preview_result = document_service.preview_chunks(text, params, page, page_size)

        return success_response(data=preview_result)

    except Exception as e:
        logger.error(f"预览文档分段失败: {e}")
        return error_response(code=400, message=str(e))


@router.post("/{doc_id}/confirm", response_model=ResponseModel)
async def confirm_document_chunks(
    doc_id: int,
    params: Optional[dict] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """确认文档分段并保存"""
    try:
        # 获取文档
        result = await db.execute(
            select(Document).where(
                Document.id == doc_id,
                Document.user_id == current_user.id
            )
        )
        document = result.scalar_one_or_none()

        if not document:
            return error_response(code=404, message="文档不存在")

        # 提取文本
        if document.file_type == 'webpage':
            web_data = await document_service.extract_text_from_url(document.url)
            text = web_data["content"]
        else:
            text = await document_service.extract_text_from_file(document)

        # 保存分段
        chunk_count = await document_service.save_chunks(doc_id, text, params, db)

        return success_response(
            data={"chunk_count": chunk_count},
            message="文档分段保存成功"
        )

    except Exception as e:
        logger.error(f"保存文档分段失败: {e}")
        return error_response(code=400, message=str(e))


@router.get("/{doc_id}/chunks", response_model=ResponseModel)
async def get_document_chunks(
    doc_id: int,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取文档分段列表"""
    try:
        # 验证文档所有权
        doc_result = await db.execute(
            select(Document).where(
                Document.id == doc_id,
                Document.user_id == current_user.id
            )
        )
        document = doc_result.scalar_one_or_none()

        if not document:
            return error_response(code=404, message="文档不存在")

        # 查询分段
        offset = (page - 1) * page_size
        result = await db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == doc_id)
            .order_by(DocumentChunk.chunk_index)
            .offset(offset)
            .limit(page_size)
        )
        chunks = result.scalars().all()

        chunk_list = [
            {
                "id": chunk.id,
                "index": chunk.chunk_index,
                "content": chunk.content,
                "char_count": chunk.char_count
            }
            for chunk in chunks
        ]

        return success_response(
            data={
                "total": document.chunk_count,
                "items": chunk_list,
                "page": page,
                "page_size": page_size
            }
        )

    except Exception as e:
        logger.error(f"获取文档分段失败: {e}")
        return error_response(code=400, message=str(e))


@router.post("/reset-all", response_model=ResponseModel)
async def reset_knowledge_base(
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    重置知识库（危险操作）
    删除所有文档记录、分块记录和向量数据库
    """
    try:
        # 1. 删除数据库中的所有文档和分块
        await db.execute(delete(DocumentChunk))
        await db.execute(delete(Document))
        await db.commit()

        logger.info(f"已清空documents和document_chunks表")

        # 2. 尝试删除向量数据库目录
        chroma_path = Path(settings.chroma_db_abs_path)
        vector_db_deleted = False
        deletion_error = None

        if chroma_path.exists():
            try:
                # 尝试删除目录
                shutil.rmtree(chroma_path)
                logger.info(f"已删除向量数据库目录: {chroma_path}")
                vector_db_deleted = True
            except (PermissionError, OSError) as e:
                deletion_error = str(e)
                logger.warning(f"向量数据库目录被占用，无法删除: {e}")

        # 3. 验证是否真的删除了
        if chroma_path.exists():
            vector_db_deleted = False
            logger.warning(f"向量数据库目录仍然存在: {chroma_path}")

        # 4. 记录操作日志
        log = SystemLog(
            user_id=current_user.id,
            action="reset_knowledge_base",
            module="document_management",
            resource="knowledge_base",
            details=f"重置知识库：删除所有文档、分块{'和向量数据' if vector_db_deleted else '（向量数据库被占用）'}",
            ip_address=get_client_ip(request)
        )
        db.add(log)
        await db.commit()

        # 5. 返回结果
        if vector_db_deleted:
            return success_response(
                message="知识库已完全重置！所有文档和向量数据已删除。",
                data={"vector_db_deleted": True}
            )
        else:
            return success_response(
                message="数据库表已清空，但向量数据库文件被占用无法删除。\n\n请按以下步骤完成清理：\n1. 停止所有Python进程\n2. 手动删除目录：D:\\00_source\\30_Python312\\13_AGENT_CC\\chroma_db\n3. 重启服务",
                data={"vector_db_deleted": False, "chroma_path": str(chroma_path)}
            )

    except Exception as e:
        await db.rollback()
        logger.error(f"重置知识库失败: {e}")
        return error_response(code=500, message=f"重置失败: {str(e)}")

