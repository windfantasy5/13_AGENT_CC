"""
智能文本分段器
优先按自然段落分段,保持语义完整
"""
import re
from typing import List, Dict


class SmartTextSplitter:
    """智能文本分段器"""

    def __init__(
        self,
        max_chunk_size: int = 500,
        min_chunk_size: int = 50,
        overlap_size: int = 50,
        paragraph_separator: str = "\n\n"
    ):
        """
        初始化分段器

        Args:
            max_chunk_size: 最大分段字符数
            min_chunk_size: 最小分段字符数
            overlap_size: 重叠字符数
            paragraph_separator: 段落分隔符
        """
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap_size = overlap_size
        self.paragraph_separator = paragraph_separator

    def split_text(self, text: str) -> List[Dict[str, any]]:
        """
        分段文本

        Args:
            text: 待分段的文本

        Returns:
            分段结果列表,每个元素包含: {index, content, char_count, start_pos, end_pos}
        """
        if not text or not text.strip():
            return []

        # 清理文本
        text = self._clean_text(text)

        # 按段落分割
        paragraphs = self._split_paragraphs(text)

        # 合并段落成块
        chunks = self._merge_paragraphs_to_chunks(paragraphs)

        # 构建结果
        results = []
        current_pos = 0
        for idx, chunk in enumerate(chunks):
            chunk_text = chunk.strip()
            if chunk_text:
                results.append({
                    "index": idx,
                    "content": chunk_text,
                    "char_count": len(chunk_text),
                    "start_pos": current_pos,
                    "end_pos": current_pos + len(chunk_text)
                })
                current_pos += len(chunk_text)

        return results

    def _clean_text(self, text: str) -> str:
        """清理文本"""
        # 统一换行符
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # 移除多余空白
        text = re.sub(r' +', ' ', text)

        # 保留段落结构,但规范化多个换行
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    def _split_paragraphs(self, text: str) -> List[str]:
        """按段落分割文本"""
        # 先按双换行分割
        paragraphs = text.split(self.paragraph_separator)

        # 如果段落太少,尝试按单换行分割
        if len(paragraphs) < 3:
            paragraphs = text.split('\n')

        # 过滤空段落
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        return paragraphs

    def _merge_paragraphs_to_chunks(self, paragraphs: List[str]) -> List[str]:
        """将段落合并成合适大小的块"""
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            para_len = len(para)

            # 如果单个段落就超过最大长度,需要按句子分割
            if para_len > self.max_chunk_size:
                # 先保存当前块
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""

                # 分割长段落
                sub_chunks = self._split_long_paragraph(para)
                chunks.extend(sub_chunks)
                continue

            # 如果加上这个段落会超过最大长度
            if len(current_chunk) + para_len + 2 > self.max_chunk_size:
                # 保存当前块
                if current_chunk:
                    chunks.append(current_chunk)

                # 开始新块
                current_chunk = para
            else:
                # 添加到当前块
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para

        # 保存最后一个块
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _split_long_paragraph(self, paragraph: str) -> List[str]:
        """分割过长的段落"""
        # 按句子分割
        sentences = self._split_sentences(paragraph)

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            sentence_len = len(sentence)

            # 如果单个句子就超过最大长度,强制分割
            if sentence_len > self.max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""

                # 按字符强制分割
                for i in range(0, sentence_len, self.max_chunk_size):
                    chunks.append(sentence[i:i + self.max_chunk_size])
                continue

            # 如果加上这个句子会超过最大长度
            if len(current_chunk) + sentence_len > self.max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence
            else:
                if current_chunk:
                    current_chunk += sentence
                else:
                    current_chunk = sentence

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """按句子分割文本"""
        # 中文句子分隔符
        sentence_endings = r'([。!?！?;；])'

        # 分割句子
        sentences = re.split(sentence_endings, text)

        # 重新组合句子和标点
        result = []
        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i] + (sentences[i + 1] if i + 1 < len(sentences) else '')
            if sentence.strip():
                result.append(sentence)

        # 处理最后一个可能没有标点的句子
        if len(sentences) % 2 == 1 and sentences[-1].strip():
            result.append(sentences[-1])

        return result

    def preview_split(self, text: str, params: Dict = None) -> Dict:
        """
        预览分段结果

        Args:
            text: 待分段文本
            params: 分段参数 {max_chunk_size, min_chunk_size, overlap_size}

        Returns:
            预览结果
        """
        # 临时更新参数
        if params:
            original_params = {
                "max_chunk_size": self.max_chunk_size,
                "min_chunk_size": self.min_chunk_size,
                "overlap_size": self.overlap_size
            }

            self.max_chunk_size = params.get("max_chunk_size", self.max_chunk_size)
            self.min_chunk_size = params.get("min_chunk_size", self.min_chunk_size)
            self.overlap_size = params.get("overlap_size", self.overlap_size)

        # 执行分段
        chunks = self.split_text(text)

        # 恢复原参数
        if params:
            self.max_chunk_size = original_params["max_chunk_size"]
            self.min_chunk_size = original_params["min_chunk_size"]
            self.overlap_size = original_params["overlap_size"]

        # 统计信息
        total_chars = sum(chunk["char_count"] for chunk in chunks)
        avg_chunk_size = total_chars / len(chunks) if chunks else 0

        return {
            "chunks": chunks,
            "total_chunks": len(chunks),
            "total_chars": total_chars,
            "avg_chunk_size": int(avg_chunk_size),
            "params": params or {
                "max_chunk_size": self.max_chunk_size,
                "min_chunk_size": self.min_chunk_size,
                "overlap_size": self.overlap_size
            }
        }
