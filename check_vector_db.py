"""
检查向量库状态
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.core.vector_store import VectorStore

def check_vector_db():
    print("=" * 60)
    print("Vector Database Status Check")
    print("=" * 60)

    vector_store = VectorStore()

    # 获取统计信息
    stats = vector_store.get_collection_stats()
    print(f"\nCollection Name: {stats['collection_name']}")
    print(f"Total Chunks: {stats['total_chunks']}")

    # 获取集合详细信息
    collection = vector_store.collection
    print(f"\nCollection ID: {collection.id}")
    print(f"Collection Metadata: {collection.metadata}")

    # 尝试获取一些数据
    if stats['total_chunks'] > 0:
        print(f"\n--- Sample Data (first 3 chunks) ---")
        results = collection.get(limit=3, include=["documents", "metadatas"])

        for i, (doc_id, doc, meta) in enumerate(zip(results['ids'], results['documents'], results['metadatas'])):
            print(f"\nChunk {i+1}:")
            print(f"  ID: {doc_id}")
            print(f"  Metadata: {meta}")
            print(f"  Content: {doc[:100]}...")
    else:
        print("\n[WARNING] Vector database is empty!")
        print("Please upload a document first.")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    check_vector_db()
