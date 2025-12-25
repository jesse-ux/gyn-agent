"""测试 Embedding 生成模块"""

import time
from embeddings import embed_single, batch_embed

print("Testing Embedding Generation")
print("="*60)

# 测试单个文本
test_text = "妇科疾病是女性常见的健康问题。"
print(f"\nTest text: {test_text}")

start = time.time()
vector = embed_single(test_text)
elapsed = time.time() - start

print(f"Vector dimension: {len(vector)}")
print(f"Generation time: {elapsed:.2f}s")
print(f"First 5 values: {vector[:5]}")

# 测试批量生成
print("\n" + "="*60)
print("Testing batch embedding")

test_texts = [
    "妇科疾病是女性常见的健康问题。",
    "产前检查对母婴健康非常重要。",
    "宫颈癌可以通过疫苗预防。",
    "月经不调可能由多种原因引起。",
    "更年期是女性生理变化的正常阶段。",
]

start = time.time()
vectors = batch_embed(test_texts, show_progress=True)
elapsed = time.time() - start

print(f"\nEmbedded {len(vectors)} texts in {elapsed:.2f}s")
print(f"Average time per text: {elapsed/len(vectors):.2f}s")
