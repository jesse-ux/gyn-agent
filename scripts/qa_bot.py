"""问答机器人模块 - RAG 问答实现"""

from typing import List, Generator, Dict, Any, Tuple, Optional
from ollama import chat
from scripts.embeddings import embed_single
from scripts.chroma_store import ChromaStore
from scripts.config import EMBED_MODEL, LLM_MODEL, CHROMA_DIR, COLLECTION_NAME


class QABot:
    """妇科健康问答助手"""

    def __init__(
        self,
        embed_model: str = None,
        llm_model: str = None,
        persist_dir: str = None,
        collection_name: str = None
    ):
        self.embed_model = embed_model or EMBED_MODEL
        self.llm_model = llm_model or LLM_MODEL
        persist_dir = persist_dir or str(CHROMA_DIR)
        collection_name = collection_name or COLLECTION_NAME

        self.store = ChromaStore(persist_dir, collection_name)

        # ✅ 保留你原本的 prompt（CLI 用，仍会让模型输出“参考来源”）
        self.system_prompt_with_refs = (
            "你是面向女性用户的妇科健康科普助手。\n"
            "你只能基于【资料】回答；如果资料不足，请明确说\"资料不足以回答\"。\n"
            "不要进行诊断、不要给出具体处方/药物剂量。\n"
            "若用户描述可能的紧急情况或高风险症状，提醒尽快就医或急诊。\n"
            "回答最后输出\"参考来源：……\"并列出引用的页码。\n"
        )

        # ✅ 新增：API 用，不让模型自己编引用（引用由后端 sources 返回）
        self.system_prompt_no_refs = (
            "你是面向女性用户的妇科健康科普助手。\n"
            "你只能基于【资料】回答；如果资料不足，请明确说\"资料不足以回答\"。\n"
            "不要进行诊断、不要给出具体处方/药物剂量。\n"
            "若用户描述可能的紧急情况或高风险症状，提醒尽快就医或急诊。\n"
            "不要在回答中输出或编造“参考来源/页码/编号”，引用来源由系统单独展示。\n"
        )

        # 兼容旧属性名（如果你其他地方在用 self.system_prompt）
        self.system_prompt = self.system_prompt_with_refs

    # ---------- 新增：统一的检索函数，返回 context + sources ----------
    def retrieve(self, question: str, top_k: int = 6) -> Tuple[str, List[Dict[str, Any]]]:
        """
        检索：返回拼好的上下文 context（给 LLM）+ 结构化 sources（给前端展示）
        去重：按 (source, page) 去重，保留距离最近的
        """
        print("Embedding question...")
        q_vec = embed_single(question, model=self.embed_model)

        print("Searching knowledge base...")
        # 检索更多结果，以便去重后仍有足够数量
        res = self.store.query(q_vec, n_results=top_k * 2)

        docs = (res.get("documents") or [[]])[0] or []
        metas = (res.get("metadatas") or [[]])[0] or []
        distances = (res.get("distances") or [[]])[0] or []

        # 去重：按 (source, page) 分组，保留距离最近的
        unique_docs: Dict[Tuple[str, Any], Dict[str, Any]] = {}

        for d, m, dist in zip(docs, metas, distances):
            source = m.get("source")
            page = m.get("page")
            key = (source, page)

            # 如果这个 (source, page) 没出现过，或者当前的距离更近，则保留
            if key not in unique_docs or dist < unique_docs[key]["distance"]:
                unique_docs[key] = {
                    "doc": d,
                    "meta": m,
                    "distance": dist,
                }

        # 按 distance 排序，取前 top_k 个
        sorted_items = sorted(
            unique_docs.values(),
            key=lambda x: x["distance"]
        )[:top_k]

        # 构建上下文（给 LLM）和 sources（给前端）
        context_blocks = []
        sources: List[Dict[str, Any]] = []

        for i, item in enumerate(sorted_items, start=1):
            d = item["doc"]
            m = item["meta"]
            dist = item["distance"]

            src = {
                "rank": i,
                "source": m.get("source"),
                "page": m.get("page"),
                "chunk": m.get("chunk"),
                "distance": dist,
                # ⚠️ 注意版权/产品策略：excerpt 建议截断，不要整段展示
                "excerpt": (d[:220].replace("\n", " ").strip() if isinstance(d, str) else None),
            }
            sources.append(src)

            context_blocks.append(
                f"[{i}] 来源：{m.get('source')} 第{m.get('page')}页\n{d}"
            )

        context = "\n\n".join(context_blocks)
        print(f"After deduplication: {len(sources)} unique sources from {len(docs)} retrieved chunks")
        return context, sources

    # ---------- 原有：返回纯文本（CLI/测试不变） ----------
    def answer(self, question: str, top_k: int = 6) -> str:
        context, _sources = self.retrieve(question, top_k=top_k)

        user_prompt = (
            f"问题：{question}\n\n"
            f"资料：\n{context}\n\n"
            "请用中文回答，并尽量引用资料中的表述（但不要大段照抄）。"
        )

        print("Generating answer...")
        resp = chat(
            model=self.llm_model,
            messages=[
                {"role": "system", "content": self.system_prompt_with_refs},
                {"role": "user", "content": user_prompt},
            ],
        )
        return resp["message"]["content"]

    # ---------- 原有：流式（CLI/测试不变） ----------
    def answer_stream(self, question: str, top_k: int = 6) -> Generator[str, None, None]:
        context, _sources = self.retrieve(question, top_k=top_k)

        user_prompt = (
            f"问题：{question}\n\n"
            f"资料：\n{context}\n\n"
            "请用中文回答，并尽量引用资料中的表述（但不要大段照抄）。"
        )

        print("Generating streaming answer...")
        stream_resp = chat(
            model=self.llm_model,
            messages=[
                {"role": "system", "content": self.system_prompt_with_refs},
                {"role": "user", "content": user_prompt},
            ],
            stream=True,
        )

        for chunk in stream_resp:
            if "message" in chunk and "content" in chunk["message"]:
                content = chunk["message"]["content"]
                if content:
                    yield content

    # ---------- 新增：返回 answer + sources（给 API 用） ----------
    def answer_with_sources(self, question: str, top_k: int = 6) -> Dict[str, Any]:
        context, sources = self.retrieve(question, top_k=top_k)

        user_prompt = (
            f"问题：{question}\n\n"
            f"资料：\n{context}\n\n"
            "请用中文回答，并尽量引用资料中的表述（但不要大段照抄）。"
        )

        print("Generating answer (no refs in text)...")
        resp = chat(
            model=self.llm_model,
            messages=[
                {"role": "system", "content": self.system_prompt_no_refs},
                {"role": "user", "content": user_prompt},
            ],
        )

        return {
            "answer": resp["message"]["content"],
            "sources": sources,
        }


# ====== API 友好的便捷函数 ======
_bot_instance: Optional[QABot] = None


def _get_bot() -> QABot:
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = QABot()
    return _bot_instance


def answer_question(question: str, top_k: int = 6) -> str:
    bot = _get_bot()
    return bot.answer(question, top_k)


def qa(question: str, top_k: int = 6) -> str:
    return answer_question(question, top_k)


def answer_question_stream(question: str, top_k: int = 6):
    bot = _get_bot()
    yield from bot.answer_stream(question, top_k)


def qa_stream(question: str, top_k: int = 6):
    yield from answer_question_stream(question, top_k)


# ✅ 新增：给 FastAPI 用（结构化 sources）
def answer_question_with_sources(question: str, top_k: int = 6) -> Dict[str, Any]:
    bot = _get_bot()
    return bot.answer_with_sources(question, top_k)
