"""
诊断ChromaDB集合问题
"""
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, str(Path(__file__).parent / "backend"))

import chromadb
from chromadb.config import Settings
from app.config.settings import settings

def diagnose_chromadb():
    print("=" * 60)
    print("ChromaDB Diagnosis")
    print("=" * 60)

    chroma_path = Path(settings.CHROMA_DB_PATH)
    print(f"\nChroma Path: {chroma_path}")
    print(f"Path exists: {chroma_path.exists()}")

    # 初始化客户端
    client = chromadb.PersistentClient(
        path=str(chroma_path),
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )

    # 列出所有集合
    print("\n--- All Collections ---")
    collections = client.list_collections()
    print(f"Total collections: {len(collections)}")

    for i, col in enumerate(collections):
        print(f"\nCollection {i+1}:")
        print(f"  Name: {col.name}")
        print(f"  ID: {col.id}")
        print(f"  Metadata: {col.metadata}")

        # 获取集合中的数据量
        count = col.count()
        print(f"  Count: {count}")

        if count > 0:
            # 获取前3个样本
            results = col.get(limit=3, include=["documents", "metadatas"])
            print(f"  Sample IDs: {results['ids'][:3]}")

    # 尝试获取document_chunks集合
    print("\n--- Getting 'document_chunks' Collection ---")
    try:
        doc_collection = client.get_collection(name="document_chunks")
        print(f"Collection ID: {doc_collection.id}")
        print(f"Collection Count: {doc_collection.count()}")
    except Exception as e:
        print(f"Error: {e}")

    # 尝试创建或获取集合
    print("\n--- Get or Create 'document_chunks' ---")
    doc_collection = client.get_or_create_collection(
        name="document_chunks",
        metadata={"description": "企业知识库文档分块向量"}
    )
    print(f"Collection ID: {doc_collection.id}")
    print(f"Collection Count: {doc_collection.count()}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    diagnose_chromadb()
