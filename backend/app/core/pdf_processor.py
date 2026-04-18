"""
PDF处理器
支持纯文字PDF和OCR识别
"""
import io
from typing import Optional, Tuple
from PyPDF2 import PdfReader
import logging

logger = logging.getLogger(__name__)


class PDFProcessor:
    """PDF处理器"""

    def __init__(self):
        self.ocr_available = False
        try:
            from paddleocr import PaddleOCR
            self.ocr = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
            self.ocr_available = True
        except Exception as e:
            logger.warning(f"PaddleOCR不可用,将只支持纯文字PDF: {e}")

    def extract_text(self, file_content: bytes) -> Tuple[str, bool]:
        """
        提取PDF文本

        Args:
            file_content: PDF文件内容

        Returns:
            (提取的文本, 是否使用了OCR)
        """
        # 先尝试提取纯文字
        text, is_text_based = self._extract_text_based(file_content)

        # 如果是纯文字PDF且提取成功
        if is_text_based and text.strip():
            return text, False

        # 如果不是纯文字或提取失败,尝试OCR
        if self.ocr_available:
            logger.info("检测到非纯文字PDF,使用OCR识别")
            ocr_text = self._extract_with_ocr(file_content)
            if ocr_text.strip():
                return ocr_text, True

        # 如果OCR也失败,返回原文本
        return text, False

    def _extract_text_based(self, file_content: bytes) -> Tuple[str, bool]:
        """提取纯文字PDF"""
        try:
            pdf_file = io.BytesIO(file_content)
            reader = PdfReader(pdf_file)

            text_parts = []
            total_chars = 0

            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
                    total_chars += len(page_text.strip())

            text = "\n\n".join(text_parts)

            # 判断是否为纯文字PDF
            # 如果平均每页字符数少于100,可能是扫描版
            avg_chars_per_page = total_chars / len(reader.pages) if reader.pages else 0
            is_text_based = avg_chars_per_page > 100

            return text, is_text_based

        except Exception as e:
            logger.error(f"提取PDF文本失败: {e}")
            return "", False

    def _extract_with_ocr(self, file_content: bytes) -> str:
        """使用OCR提取PDF文本"""
        try:
            # 将PDF转换为图片
            from pdf2image import convert_from_bytes

            images = convert_from_bytes(file_content)

            text_parts = []
            for img in images:
                # OCR识别
                result = self.ocr.ocr(img, cls=True)

                # 提取文本
                if result and result[0]:
                    page_text = "\n".join([line[1][0] for line in result[0]])
                    text_parts.append(page_text)

            return "\n\n".join(text_parts)

        except ImportError:
            logger.error("pdf2image未安装,无法进行OCR")
            return ""
        except Exception as e:
            logger.error(f"OCR识别失败: {e}")
            return ""

    def is_text_based_pdf(self, file_content: bytes) -> bool:
        """判断是否为纯文字PDF"""
        _, is_text_based = self._extract_text_based(file_content)
        return is_text_based
