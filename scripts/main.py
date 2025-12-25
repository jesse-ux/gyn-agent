"""主入口 - 建立索引并运行问答测试"""

from pathlib import Path
from tqdm import tqdm

from config import *
from pdf_parser import extract_pages, clean_text
from text_splitter import split_sentences, chunk_by_sentences
from embeddings import batch_embed
from chroma_store import ChromaStore
from qa_bot import QABot


def build_index(pdf_paths: list) -> None:
    """
    从 PDF 文件构建向量索引

    Args:
        pdf_paths: PDF 文件路径列表
    """
    store = ChromaStore(
        persist_dir=str(CHROMA_DIR),
        collection_name=COLLECTION_NAME
    )

    for pdf_path in pdf_paths:
        pdf_path = str(pdf_path)
        book_name = Path(pdf_path).name
        stem = Path(pdf_path).stem

        print(f"\n{'='*60}")
        print(f"Processing: {book_name}")
        print(f"{'='*60}")

        # 1. 提取页面
        print("Step 1: Extracting pages...")
        pages = extract_pages(pdf_path)
        print(f"  Found {len(pages)} pages")

        # 2. 分句和切分
        print("\nStep 2: Splitting sentences and chunking...")
        ids, docs, metas = [], [], []

        for p in tqdm(pages, desc="  Processing pages"):
            page_text = clean_text(p["text"])
            if not page_text:
                continue

            # HanLP 分句
            sentences = split_sentences(page_text)
            # 按 chunk 切分
            chunks = chunk_by_sentences(
                sentences,
                max_chars=MAX_CHARS_PER_CHUNK,
                overlap_sents=OVERLAP_SENTENCES
            )

            for ci, chunk in enumerate(chunks):
                doc_id = f"{stem}_p{p['page']}_c{ci}"
                ids.append(doc_id)
                docs.append(chunk)
                metas.append({
                    "source": book_name,
                    "page": p["page"],
                    "chunk": ci,
                })

        print(f"  Created {len(docs)} chunks")

        if not docs:
            print("  No text extracted, skipping...")
            continue

        # 3. 生成 embeddings
        print(f"\nStep 3: Generating embeddings...")
        vectors = batch_embed(
            docs,
            model=EMBED_MODEL,
            batch_size=EMBED_BATCH_SIZE,
            show_progress=True
        )

        # 4. 存入数据库
        print(f"\nStep 4: Storing in ChromaDB...")
        store.add_documents(ids, docs, vectors, metas)

    print(f"\n{'='*60}")
    print("✅ Index built successfully!")
    print(f"{'='*60}\n")

    # 显示统计信息
    info = store.get_collection_info()
    print(f"Collection: {info['name']}")
    print(f"Total documents: {info['count']}")


def main():
    """主函数"""
    pdf_files = [
        PDF_DIR / "妇产科学.pdf",
    ]

    # 过滤不存在的文件
    pdf_files = [f for f in pdf_files if f.exists()]

    if not pdf_files:
        print(f"❌ No PDF files found in {PDF_DIR}")
        return

    # 建立索引
    build_index(pdf_files)

    # 测试问答
    print("\n" + "="*60)
    print("Testing Q&A")
    print("="*60 + "\n")

    bot = QABot(
        embed_model=EMBED_MODEL,
        llm_model=LLM_MODEL,
        persist_dir=str(CHROMA_DIR),
        collection_name=COLLECTION_NAME
    )

    test_questions = [
        "什么是细菌性阴道炎？有哪些典型表现？",
    ]

    for question in test_questions:
        print(f"问题: {question}\n")
        answer = bot.answer(question, top_k=DEFAULT_TOP_K)
        print(f"答案:\n{answer}\n")
        print("-" * 60 + "\n")


if __name__ == "__main__":
    main()
