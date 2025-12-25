"""测试 PDF 解析模块"""

from pdf_parser import extract_pages, clean_text

pdf_path = "../data/pdfs/妇产科学.pdf"

print("Testing PDF Parser")
print("="*60)

# 提取第 1 页
pages = extract_pages(pdf_path)
print(f"Total pages: {len(pages)}")

# 显示第 1 页原文
print(f"\n--- Page 1 (raw) ---")
print(pages[0]["text"][:300])

# 显示清理后的文本
print(f"\n--- Page 1 (cleaned) ---")
cleaned = clean_text(pages[0]["text"])
print(cleaned[:300])

print(f"\nTotal chars in page 1: {len(cleaned)}")
