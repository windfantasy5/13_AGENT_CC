"""
手动处理pending状态的文档
重新提取文本、分段并向量化
"""
import asyncio
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.config.database import get_db
from app.models.document import Document
from app.services.document_service import DocumentService
from sqlalchemy import select

async def process_pending_documents():
    print("=" * 60)
    print("Processing Pending Documents")
    print("=" * 60)

    doc_service = DocumentService()

    async for db in get_db():
        # 查找pending状态的文档
        result = await db.execute(
            select(Document).where(Document.status == 'pending')
        )
        pending_docs = result.scalars().all()

        print(f"\nFound {len(pending_docs)} pending documents")

        for doc in pending_docs:
            print(f"\n--- Processing Document {doc.id}: {doc.title} ---")

            try:
                # 提取文本
                print(f"  [1] Extracting text...")
                text = await doc_service.extract_text_from_file(doc)
                print(f"  [OK] Extracted {len(text)} characters")

                # 保存分段到向量数据库
                print(f"  [2] Chunking and vectorizing...")
                params = {
                    "max_chunk_size": 500,
                    "min_chunk_size": 50,
                    "overlap_size": 50
                }
                chunk_count = await doc_service.save_chunks(doc.id, text, params, db)

                print(f"  [OK] Created {chunk_count} chunks")

                # 更新文档状态
                doc.status = 'completed'
                doc.chunk_count = chunk_count
                await db.commit()

                print(f"  [SUCCESS] Document {doc.id} processed successfully")

            except Exception as e:
                print(f"  [FAIL] Error processing document {doc.id}: {e}")
                import traceback
                traceback.print_exc()

                # 更新错误信息
                doc.status = 'failed'
                doc.error_message = str(e)
                await db.commit()

        break

    print("\n" + "=" * 60)
    print("Processing completed")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(process_pending_documents())
