"""
重新向量化已完成但vector_id为空的文档
"""
import asyncio
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.config.database import get_db
from app.models.document import Document, DocumentChunk
from app.core.vector_store import VectorStore
from sqlalchemy import select

async def revectorize_documents():
    print("=" * 60)
    print("Re-vectorizing Documents")
    print("=" * 60)

    vector_store = VectorStore()

    async for db in get_db():
        # 查找已完成但没有向量化的文档
        result = await db.execute(
            select(Document).where(Document.status == 'completed')
        )
        completed_docs = result.scalars().all()

        print(f"\nFound {len(completed_docs)} completed documents")

        for doc in completed_docs:
            # 检查该文档的分块
            chunk_result = await db.execute(
                select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
            )
            chunks = chunk_result.scalars().all()

            if not chunks:
                print(f"\n[SKIP] Document {doc.id}: {doc.title} - No chunks")
                continue

            # 检查是否有vector_id为空的分块
            chunks_without_vector = [c for c in chunks if c.vector_id is None]

            if not chunks_without_vector:
                print(f"\n[OK] Document {doc.id}: {doc.title} - Already vectorized ({len(chunks)} chunks)")
                continue

            print(f"\n--- Re-vectorizing Document {doc.id}: {doc.title} ---")
            print(f"  Total chunks: {len(chunks)}")
            print(f"  Chunks without vector: {len(chunks_without_vector)}")

            try:
                # 准备数据
                chunk_ids = [c.id for c in chunks_without_vector]
                contents = [c.content for c in chunks_without_vector]
                metadatas = [
                    {
                        "document_id": doc.id,
                        "chunk_index": c.chunk_index,
                        "char_count": c.char_count
                    }
                    for c in chunks_without_vector
                ]

                # 向量化
                print(f"  [1] Generating embeddings...")
                vector_ids = vector_store.add_chunks(
                    chunk_ids=chunk_ids,
                    contents=contents,
                    metadatas=metadatas
                )

                # 更新数据库
                print(f"  [2] Updating database...")
                for i, chunk in enumerate(chunks_without_vector):
                    chunk.vector_id = vector_ids[i]

                await db.commit()

                print(f"  [SUCCESS] Vectorized {len(vector_ids)} chunks")

            except Exception as e:
                print(f"  [FAIL] Error: {e}")
                import traceback
                traceback.print_exc()

        break

    # 显示最终统计
    print("\n" + "=" * 60)
    stats = vector_store.get_collection_stats()
    print(f"Vector DB Status: {stats['total_chunks']} chunks")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(revectorize_documents())
