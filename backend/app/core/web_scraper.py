"""
网页爬虫和内容清洗
提取网页主体正文,去除广告、侧边栏等干扰信息，并转换为Markdown格式
"""
import httpx
from bs4 import BeautifulSoup
from readability import Document
import logging
from typing import Optional, Dict
import html2text

logger = logging.getLogger(__name__)


class WebScraper:
    """网页爬虫"""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        # 初始化HTML转Markdown工具
        self.html2text = html2text.HTML2Text()
        self.html2text.ignore_links = False
        self.html2text.ignore_images = False
        self.html2text.body_width = 0  # 不自动换行

    async def fetch_and_extract(self, url: str) -> Dict[str, str]:
        """
        抓取并提取网页内容，返回Markdown格式

        Args:
            url: 网页URL

        Returns:
            {title, content, markdown, url}
        """
        try:
            # 抓取网页
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                html_content = response.text

            # 提取主体内容
            title, cleaned_html = self._extract_main_content(html_content)

            # 转换为纯文本
            text_content = self._html_to_text(cleaned_html)

            # 转换为Markdown
            markdown_content = self._html_to_markdown(cleaned_html)

            return {
                "title": title or "未命名文档",
                "content": text_content,  # 纯文本（用于向量化）
                "markdown": markdown_content,  # Markdown格式（用于预览）
                "url": url
            }

        except httpx.TimeoutException:
            logger.error(f"网页请求超时: {url}")
            raise Exception("网页请求超时")
        except httpx.HTTPError as e:
            logger.error(f"网页请求失败: {url}, 错误: {e}")
            raise Exception(f"网页请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"网页处理失败: {url}, 错误: {e}")
            raise Exception(f"网页处理失败: {str(e)}")

    def _extract_main_content(self, html: str) -> tuple[str, str]:
        """
        提取网页主体内容（清洗后的HTML）

        Args:
            html: HTML内容

        Returns:
            (标题, 清洗后的HTML)
        """
        # 使用readability提取主体内容
        doc = Document(html)
        title = doc.title()
        summary_html = doc.summary()

        # 使用BeautifulSoup清洗HTML
        soup = BeautifulSoup(summary_html, 'html.parser')

        # 移除脚本和样式
        for script in soup(["script", "style", "noscript"]):
            script.decompose()

        # 移除常见的干扰元素
        for element in soup.find_all(class_=lambda x: x and any(
            keyword in str(x).lower() for keyword in
            ['ad', 'advertisement', 'sidebar', 'comment', 'footer', 'header', 'nav', 'menu']
        )):
            element.decompose()

        # 移除ID包含干扰关键词的元素
        for element in soup.find_all(id=lambda x: x and any(
            keyword in str(x).lower() for keyword in
            ['ad', 'sidebar', 'comment', 'footer', 'header', 'nav']
        )):
            element.decompose()

        return title, str(soup)

    def _html_to_text(self, html: str) -> str:
        """将HTML转换为纯文本"""
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(separator='\n', strip=True)
        return self._clean_text(text)

    def _html_to_markdown(self, html: str) -> str:
        """将HTML转换为Markdown格式"""
        try:
            markdown = self.html2text.handle(html)
            return markdown.strip()
        except Exception as e:
            logger.warning(f"HTML转Markdown失败，降级为纯文本: {e}")
            return self._html_to_text(html)

    def _clean_text(self, text: str) -> str:
        """清理文本"""
        # 移除多余空行
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]

        # 重新组合
        text = '\n\n'.join(lines)

        return text
