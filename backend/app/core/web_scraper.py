"""
网页爬虫和内容清洗
提取网页主体正文,去除广告、侧边栏等干扰信息
"""
import httpx
from bs4 import BeautifulSoup
from readability import Document
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class WebScraper:
    """网页爬虫"""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    async def fetch_and_extract(self, url: str) -> Dict[str, str]:
        """
        抓取并提取网页内容

        Args:
            url: 网页URL

        Returns:
            {title, content, url}
        """
        try:
            # 抓取网页
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                html_content = response.text

            # 提取主体内容
            title, content = self._extract_main_content(html_content)

            return {
                "title": title or "未命名文档",
                "content": content,
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
        提取网页主体内容

        Args:
            html: HTML内容

        Returns:
            (标题, 正文内容)
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

        # 提取文本
        text = soup.get_text(separator='\n', strip=True)

        # 清理文本
        text = self._clean_text(text)

        return title, text

    def _clean_text(self, text: str) -> str:
        """清理文本"""
        # 移除多余空行
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]

        # 重新组合
        text = '\n\n'.join(lines)

        return text
