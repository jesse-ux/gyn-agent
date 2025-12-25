"""PDF 解析和文本清理模块"""

from pathlib import Path
from typing import List, Dict, Any
import re
import fitz  # PyMuPDF


def extract_pages(pdf_path: str) -> List[Dict[str, Any]]:
    """
    从 PDF 提取每一页的文本

    Args:
        pdf_path: PDF 文件路径

    Returns:
        包含页码和文本的字典列表
    """
    doc = fitz.open(pdf_path)
    pages = []
    for i in range(doc.page_count):
        page = doc.load_page(i)
        text = page.get_text("text")
        pages.append({"page": i + 1, "text": text})
    return pages


def clean_text(t: str) -> str:
    """
    清理文本：替换特殊字符、合并多余空行

    Args:
        t: 原始文本

    Returns:
        清理后的文本
    """
    t = t.replace("\u00a0", " ")
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


if __name__ == "__main__":
    # 测试代码
    pdf_path = "../data/pdfs/妇产科学.pdf"
    pages = extract_pages(pdf_path)
    print(f"总共 {len(pages)} 页")
    print(f"\n第 1 页原文：\n{pages[0]['text'][:200]}...")
    print(f"\n第 1 页清理后：\n{clean_text(pages[0]['text'])[:200]}...")
