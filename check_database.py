"""
检查数据库中的文档和分块记录
"""
import asyncio
import sys
import io
from pathlib import Path

# Set UTF-8 encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.config.database import get_db
from app.models.document import Document, DocumentChunk
from sqlalchemy import select

async def check_database():
    print("=" * 60)
    print("Database Status Check")
    print("=" * 60)

    async for db in get_db():
        # 检查文档
        result = await db.execute(select(Document))
        documents = result.scalars().all()

        print(f"\nTotal Documents: {len(documents)}")

        for doc in documents[:5]:  # 只显示前5个
            print(f"\n--- Document {doc.id} ---")
            print(f"  Title: {doc.title}")
            print(f"  Type: {doc.file_type}")
            print(f"  Status: {doc.status}")
            print(f"  Chunk Count: {doc.chunk_count}")
            print(f"  File Path: {doc.file_path}")

            # 检查该文档的分块
            chunk_result = await db.execute(
                select(DocumentChunk).where(DocumentChunk.document_id == doc.id).limit(3)
            )
            chunks = chunk_result.scalars().all()

            print(f"  Chunks in DB: {len(chunks)}")
            if chunks:
                print(f"  First chunk vector_id: {chunks[0].vector_id}")
                print(f"  First chunk content: {chunks[0].content[:50]}...")

        break

    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(check_database())
