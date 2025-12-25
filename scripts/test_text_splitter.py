"""测试文本切分模块"""

from pdf_parser import extract_pages, clean_text
from text_splitter import split_sentences, chunk_by_sentences

pdf_path = "../data/pdfs/妇产科学.pdf"

print("Testing Text Splitter")
print("="*60)

# 提取第 1 页
pages = extract_pages(pdf_path)
page_text = clean_text(pages[0]["text"])

# 分句
sentences = split_sentences(page_text)
print(f"Total sentences: {len(sentences)}")

# 显示前 5 句
print("\nFirst 5 sentences:")
for i, s in enumerate(sentences[:5], 1):
    print(f"  {i}. {s}")

# 切分成 chunks
chunks = chunk_by_sentences(sentences, max_chars=900, overlap_sents=2)
print(f"\nTotal chunks: {len(chunks)}")

# 显示前 2 个 chunks
print("\nFirst 2 chunks:")
for i, chunk in enumerate(chunks[:2], 1):
    print(f"\nChunk {i} ({len(chunk)} chars):")
    print(f"  {chunk[:200]}...")
