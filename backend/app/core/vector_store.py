"""
向量存储管理模块
使用Chroma向量数据库存储文档向量
"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import logging
from pathlib import Path
from openai import OpenAI
from app.config.settings import settings

logger = logging.getLogger(__name__)


class VectorStore:
    """向量存储管理类"""

    def __init__(self):
        """初始化Chroma客户端"""
        # 创建Chroma存储目录
        chroma_path = Path(settings.CHROMA_DB_PATH)
        chroma_path.mkdir(parents=True, exist_ok=True)

        # 初始化Chroma客户端
        self.client = chromadb.PersistentClient(
            path=str(chroma_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # 初始化OpenAI客户端用于生成向量
        self.openai_client = OpenAI(
            api_key=settings.DASHSCOPE_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name="document_chunks",
            metadata={"description": "企业知识库文档分块向量"}
        )

        logger.info(f"向量存储初始化完成，存储路径: {chroma_path}")

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        生成文本向量
        DashScope API限制：每次最多10个文本

        Args:
            texts: 文本列表

        Returns:
            向量列表
        """
        try:
            all_embeddings = []
            batch_size = 10  # DashScope API限制

            # 分批处理
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]

                response = self.openai_client.embeddings.create(
                    model="text-embedding-v4",
                    input=batch,
                    encoding_format="float"
                )

                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)

                logger.info(f"成功生成批次 {i//batch_size + 1} 的 {len(batch_embeddings)} 个向量")

            logger.info(f"总共生成 {len(all_embeddings)} 个向量")
            return all_embeddings
        except Exception as e:
            logger.error(f"生成向量失败: {e}")
            raise Exception(f"向量生成失败: {str(e)}")

    def add_chunks(
        self,
        chunk_ids: List[int],
        contents: List[str],
        metadatas: List[Dict]
    ) -> List[str]:
        """
        添加文档分块到向量库

        Args:
            chunk_ids: 分块ID列表
            contents: 分块内容列表
            metadatas: 元数据列表

        Returns:
            向量ID列表
        """
        try:
            # 生成向量
            embeddings = self.generate_embeddings(contents)

            # 转换ID为字符串
            vector_ids = [f"chunk_{chunk_id}" for chunk_id in chunk_ids]

            # 添加到Chroma
            self.collection.add(
                ids=vector_ids,
                embeddings=embeddings,
                documents=contents,
                metadatas=metadatas
            )

            logger.info(f"成功添加 {len(vector_ids)} 个分块到向量库")
            return vector_ids

        except Exception as e:
            logger.error(f"添加分块到向量库失败: {e}")
            raise Exception(f"向量存储失败: {str(e)}")

    def search_similar(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> Dict:
        """
        相似度检索

        Args:
            query: 查询文本
            top_k: 返回结果数量
            filter_metadata: 元数据过滤条件

        Returns:
            检索结果
        """
        try:
            # 生成查询向量
            query_embedding = self.generate_embeddings([query])[0]

            # 执行检索
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_metadata
            )

            # 格式化结果
            formatted_results = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        "id": results['ids'][0][i],
                        "content": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i],
                        "distance": results['distances'][0][i] if 'distances' in results else None
                    })

            logger.info(f"检索到 {len(formatted_results)} 个相似结果")
            return {
                "results": formatted_results,
                "total": len(formatted_results)
            }

        except Exception as e:
            logger.error(f"相似度检索失败: {e}")
            raise Exception(f"检索失败: {str(e)}")

    def delete_chunks(self, chunk_ids: List[int]) -> bool:
        """
        删除文档分块

        Args:
            chunk_ids: 分块ID列表

        Returns:
            是否成功
        """
        try:
            vector_ids = [f"chunk_{chunk_id}" for chunk_id in chunk_ids]
            self.collection.delete(ids=vector_ids)
            logger.info(f"成功删除 {len(vector_ids)} 个分块")
            return True
        except Exception as e:
            logger.error(f"删除分块失败: {e}")
            return False

    def delete_document_chunks(self, document_id: int) -> bool:
        """
        删除文档的所有分块

        Args:
            document_id: 文档ID

        Returns:
            是否成功
        """
        try:
            self.collection.delete(
                where={"document_id": document_id}
            )
            logger.info(f"成功删除文档 {document_id} 的所有分块")
            return True
        except Exception as e:
            logger.error(f"删除文档分块失败: {e}")
            return False

    def get_collection_stats(self) -> Dict:
        """
        获取集合统计信息

        Returns:
            统计信息
        """
        try:
            count = self.collection.count()
            return {
                "total_chunks": count,
                "collection_name": self.collection.name
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {"total_chunks": 0, "collection_name": "unknown"}
