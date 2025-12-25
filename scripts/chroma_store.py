"""ChromaDB 向量数据库模块"""

from pathlib import Path
from typing import List, Dict, Any, Tuple
import chromadb


class ChromaStore:
    """ChromaDB 向量数据库封装"""

    def __init__(
        self,
        persist_dir: str = "../data/chroma",
        collection_name: str = "gyn_kb"
    ):
        """
        初始化 ChromaDB 客户端

        Args:
            persist_dir: 数据持久化目录
            collection_name: 集合名称
        """
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection_name = collection_name
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},  # cosine/l2/ip
        )

    def add_documents(
        self,
        ids: List[str],
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]]
    ) -> None:
        """
        批量添加文档到向量数据库

        Args:
            ids: 文档 ID 列表
            documents: 文档内容列表
            embeddings: 向量列表
            metadatas: 元数据列表
        """
        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        print(f"Added {len(documents)} documents to collection '{self.collection_name}'")

    def query(
        self,
        query_embedding: List[float],
        n_results: int = 5
    ) -> Dict[str, Any]:
        """
        向量检索

        Args:
            query_embedding: 查询向量
            n_results: 返回结果数量

        Returns:
            检索结果，包含 documents, metadatas, distances
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        return results

    def get_collection_info(self) -> Dict[str, Any]:
        """获取集合信息"""
        count = self.collection.count()
        return {
            "name": self.collection_name,
            "count": count,
        }

    def clear_collection(self) -> None:
        """清空集合"""
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        print(f"Collection '{self.collection_name}' cleared")


if __name__ == "__main__":
    # 测试代码
    store = ChromaStore()

    info = store.get_collection_info()
    print(f"Collection info: {info}")

    # 测试添加文档
    test_docs = [
        "妇科疾病包括阴道炎、宫颈炎等。",
        "产前检查是孕期保健的重要环节。",
    ]

    from embeddings import batch_embed
    vectors = batch_embed(test_docs, show_progress=False)

    store.add_documents(
        ids=["test_1", "test_2"],
        documents=test_docs,
        embeddings=vectors,
        metadatas=[
            {"source": "test", "page": 1},
            {"source": "test", "page": 2},
        ]
    )

    # 测试检索
    query_text = "什么是妇科疾病？"
    query_vec = batch_embed([query_text], show_progress=False)[0]

    results = store.query(query_vec, n_results=2)
    print("\nQuery results:")
    for i, (doc, meta, dist) in enumerate(zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ), 1):
        print(f"\n[{i}] Distance: {dist:.4f}")
        print(f"    Source: {meta}")
        print(f"    Content: {doc[:80]}...")
