"""
高级中文分词器
支持停用词过滤、词性标注、自定义词典
"""
import jieba
import jieba.posseg as pseg
from pathlib import Path
from typing import List, Set
import logging

logger = logging.getLogger(__name__)


class AdvancedTokenizer:
    """高级中文分词器"""

    def __init__(self):
        self.stopwords = self._load_stopwords()
        self._load_custom_dict()
        logger.info(f"分词器初始化完成，停用词数量: {len(self.stopwords)}")

    def tokenize(self, text: str, use_pos_filter: bool = True) -> List[str]:
        """
        中文分词

        Args:
            text: 输入文本
            use_pos_filter: 是否使用词性过滤

        Returns:
            分词结果列表
        """
        if not text or not text.strip():
            return []

        if use_pos_filter:
            # 词性标注分词
            words = pseg.lcut(text)
            tokens = []

            for word, flag in words:
                # 保留名词(n)、动词(v)、形容词(a)、专有名词(nr/ns/nt)
                if self._should_keep_word(word, flag):
                    tokens.append(word.lower())

            return tokens
        else:
            # 基础分词（不做词性过滤）
            tokens = jieba.lcut(text)
            return [
                t.lower().strip()
                for t in tokens
                if self._is_valid_token(t)
            ]

    def _should_keep_word(self, word: str, flag: str) -> bool:
        """
        判断是否保留该词

        Args:
            word: 词语
            flag: 词性标记

        Returns:
            是否保留
        """
        # 过滤条件
        if not self._is_valid_token(word):
            return False

        # 词性过滤：保留名词、动词、形容词、专有名词
        if flag.startswith(('n', 'v', 'a')) or flag in ['nr', 'ns', 'nt', 'nz']:
            return True

        # 保留英文和数字组合
        if flag in ['eng', 'x'] and len(word) > 1:
            return True

        return False

    def _is_valid_token(self, token: str) -> bool:
        """
        判断token是否有效

        Args:
            token: 词语

        Returns:
            是否有效
        """
        token = token.strip()

        # 长度过滤
        if len(token) < 2:
            return False

        # 停用词过滤
        if token in self.stopwords:
            return False

        # 过滤纯标点符号
        if all(not c.isalnum() for c in token):
            return False

        return True

    def _load_stopwords(self) -> Set[str]:
        """
        加载停用词表

        Returns:
            停用词集合
        """
        stopwords = set()

        # 尝试加载自定义停用词
        from app.config.settings import PROJECT_ROOT
        stopwords_file = PROJECT_ROOT / "backend" / "data" / "stopwords.txt"

        if stopwords_file.exists():
            try:
                with open(stopwords_file, 'r', encoding='utf-8') as f:
                    stopwords = set(line.strip() for line in f if line.strip())
                logger.info(f"加载停用词表: {stopwords_file}, 数量: {len(stopwords)}")
            except Exception as e:
                logger.warning(f"加载停用词表失败: {e}")

        # 如果没有自定义停用词，使用默认停用词
        if not stopwords:
            stopwords = self._get_default_stopwords()
            logger.info(f"使用默认停用词表，数量: {len(stopwords)}")

        return stopwords

    def _get_default_stopwords(self) -> Set[str]:
        """
        获取默认停用词表

        Returns:
            停用词集合
        """
        return {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人',
            '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去',
            '你', '会', '着', '没有', '看', '好', '自己', '这', '个', '们',
            '能', '对', '他', '她', '它', '这个', '那个', '什么', '怎么',
            '为什么', '哪里', '谁', '多少', '几', '第', '些', '那些', '这些',
            '及', '其', '与', '或', '但', '而', '因为', '所以', '如果', '虽然',
            '然而', '可是', '不过', '只是', '只有', '才', '就是', '还是', '已经',
            '正在', '曾经', '将要', '可能', '应该', '必须', '需要', '想要',
            '啊', '呀', '吗', '吧', '呢', '哦', '哈', '嗯', '唉'
        }

    def _load_custom_dict(self):
        """加载自定义词典"""
        from app.config.settings import PROJECT_ROOT
        dict_file = PROJECT_ROOT / "backend" / "data" / "custom_dict.txt"

        if dict_file.exists():
            try:
                jieba.load_userdict(str(dict_file))
                logger.info(f"加载自定义词典: {dict_file}")
            except Exception as e:
                logger.warning(f"加载自定义词典失败: {e}")

    def tokenize_batch(self, texts: List[str], use_pos_filter: bool = True) -> List[List[str]]:
        """
        批量分词

        Args:
            texts: 文本列表
            use_pos_filter: 是否使用词性过滤

        Returns:
            分词结果列表
        """
        return [self.tokenize(text, use_pos_filter) for text in texts]
