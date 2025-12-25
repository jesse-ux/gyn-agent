"""Embedding 生成模块 - 调用 Ollama 生成文本向量"""

from typing import List
from tqdm import tqdm
from ollama import embed


def batch_embed(
    texts: List[str],
    model: str = "dengcao/Qwen3-Embedding-0.6B:Q8_0",
    batch_size: int = 32,
    show_progress: bool = True
) -> List[List[float]]:
    """
    批量生成文本 embeddings

    Args:
        texts: 文本列表
        model: Ollama embedding 模型名称
        batch_size: 每批处理的文本数量
        show_progress: 是否显示进度条

    Returns:
        向量列表，每个向量是一个 float 数组
    """
    vectors: List[List[float]] = []

    # 创建批次数组
    batches = [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)]

    iterator = tqdm(batches, desc="Generating embeddings", disable=not show_progress)

    for batch in iterator:
        try:
            resp = embed(model=model, input=batch)
            vectors.extend(resp["embeddings"])
            iterator.set_postfix({"embedded": len(vectors), "total": len(texts)})
        except Exception as e:
            print(f"\nError embedding batch: {e}")
            raise

    return vectors


def embed_single(
    text: str,
    model: str = "dengcao/Qwen3-Embedding-0.6B:Q8_0"
) -> List[float]:
    """
    生成单个文本的 embedding

    Args:
        text: 单个文本
        model: Ollama embedding 模型名称

    Returns:
        向量（float 数组）
    """
    resp = embed(model=model, input=text)
    return resp["embeddings"][0]


if __name__ == "__main__":
    # 测试代码
    test_texts = [
        "妇科疾病是女性常见的健康问题。",
        "产前检查对母婴健康非常重要。",
        "宫颈癌可以通过疫苗预防。",
    ]

    print("测试 embedding 生成...")
    vectors = batch_embed(test_texts, show_progress=True)

    print(f"\n生成了 {len(vectors)} 个向量")
    print(f"向量维度: {len(vectors[0])}")
    print(f"第一个向量前 5 个值: {vectors[0][:5]}")
