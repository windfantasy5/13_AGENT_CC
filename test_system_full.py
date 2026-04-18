"""
Complete system test script
Test: Document upload -> Vectorization -> RAG retrieval -> Streaming response
"""
import asyncio
import sys
from pathlib import Path
import io

# Set UTF-8 encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.document_service import DocumentService
from app.services.rag_service import RAGService
from app.services.chat_service import ChatService
from app.config.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession


async def test_full_workflow():
    """Test complete workflow"""
    print("=" * 60)
    print("Starting complete system test")
    print("=" * 60)

    # 1. Test document service
    print("\n[1] Testing document service...")
    doc_service = DocumentService()

    # Create test text
    test_text = """
    人工智能（Artificial Intelligence，AI）是计算机科学的一个分支。
    它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。
    该领域的研究包括机器人、语言识别、图像识别、自然语言处理和专家系统等。

    机器学习是人工智能的一个重要分支。它是一门多领域交叉学科，涉及概率论、统计学、
    逼近论、凸分析、算法复杂度理论等多门学科。机器学习专门研究计算机怎样模拟或实现
    人类的学习行为，以获取新的知识或技能，重新组织已有的知识结构使之不断改善自身的性能。

    深度学习是机器学习的一个子集，它使用多层神经网络来学习数据的表示。
    深度学习在图像识别、语音识别、自然语言处理等领域取得了突破性进展。
    """

    # Test chunk preview
    preview = doc_service.preview_chunks(test_text, {
        "max_chunk_size": 200,
        "min_chunk_size": 50,
        "overlap_size": 20
    })
    print(f"[OK] Document chunking: {preview['total_chunks']} chunks")
    print(f"  Average chunk size: {preview['avg_chunk_size']} chars")

    # 2. Test vector storage
    print("\n[2] Testing vector storage...")
    from app.core.vector_store import VectorStore
    vector_store = VectorStore()

    stats = vector_store.get_collection_stats()
    print(f"[OK] Vector DB status: {stats['total_chunks']} chunks")

    # Test adding vectors (using temporary data)
    try:
        test_chunks = preview['chunks'][:2]  # Only test first 2
        chunk_ids = [9999, 10000]  # Temporary IDs
        contents = [c['content'] for c in test_chunks]
        metadatas = [{"document_id": 9999, "chunk_index": i} for i in range(len(test_chunks))]

        vector_ids = vector_store.add_chunks(chunk_ids, contents, metadatas)
        print(f"[OK] Vector addition: {len(vector_ids)} vectors")

        # Test retrieval
        search_result = vector_store.search_similar("什么是人工智能", top_k=2)
        print(f"[OK] Vector search: found {len(search_result['results'])} results")
        if search_result['results']:
            print(f"  Most similar: {search_result['results'][0]['content'][:50]}...")

        # Cleanup test data
        vector_store.delete_chunks(chunk_ids)
        print(f"[OK] Test data cleaned")

    except Exception as e:
        print(f"[FAIL] Vector storage test failed: {e}")

    # 3. Test RAG service
    print("\n[3] Testing RAG service...")
    rag_service = RAGService()

    try:
        # If vector DB has data, test retrieval
        if stats['total_chunks'] > 0:
            search_result = await rag_service.search_knowledge(
                query="人工智能是什么",
                top_k=3
            )
            print(f"[OK] RAG retrieval: found {len(search_result['results'])} results")
            if search_result['results']:
                print(f"  Similarity score: {search_result['results'][0]['score']:.2f}")
        else:
            print("[WARN] Vector DB is empty, skipping RAG test")
    except Exception as e:
        print(f"[FAIL] RAG retrieval failed: {e}")

    # 4. Test LLM streaming
    print("\n[4] Testing LLM streaming...")
    from app.services.llm_service import LLMService
    llm_service = LLMService()

    try:
        # Check if streaming method exists
        if hasattr(llm_service, 'chat_completion_stream'):
            print("[OK] LLM streaming method implemented")

            # Test streaming call
            messages = [{"role": "user", "content": "你好，请用一句话介绍你自己"}]
            chunks = []

            async for chunk in llm_service.chat_completion_stream(messages, max_tokens=50):
                chunks.append(chunk.get("content", ""))

            full_response = "".join(chunks)
            print(f"[OK] Streaming call: received {len(chunks)} chunks")
            print(f"  Full response: {full_response[:100]}...")
        else:
            print("[FAIL] LLM streaming method not implemented")
    except Exception as e:
        print(f"[FAIL] LLM streaming failed: {e}")

    print("\n" + "=" * 60)
    print("Test completed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_full_workflow())
