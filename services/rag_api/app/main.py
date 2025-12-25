# services/rag_api/app/main.py
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from ollama import chat  # 用于流式时直接 chat（避免重复检索时也可用）

# --- 让 FastAPI 服务能 import 到项目根目录下的 scripts/ ---
PROJECT_ROOT = Path(__file__).resolve().parents[3]  # .../gyn-agent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _load_qa_bot():
    try:
        import scripts.qa_bot as qa_bot
        return qa_bot
    except Exception as e:
        raise RuntimeError(f"Failed to import scripts.qa_bot: {e}")


# ====== 1) 适配你现有的 QA 函数（返回 answer + sources） ======
def run_qa(question: str, top_k: int = 6) -> Dict[str, Any]:
    qa_bot = _load_qa_bot()

    # ✅ 优先使用结构化接口
    if hasattr(qa_bot, "answer_question_with_sources"):
        return qa_bot.answer_question_with_sources(question, top_k=top_k)

    # fallback：退回旧接口（不建议长期用）
    if hasattr(qa_bot, "answer_question"):
        ans = qa_bot.answer_question(question, top_k=top_k)
        return {"answer": ans, "sources": []}

    raise RuntimeError("qa_bot.py 里没找到可用的问答函数。")


# ====== 2) Schema ======
class QARequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(6, ge=1, le=20)


class SourceItem(BaseModel):
    rank: int
    source: Optional[str] = None
    page: Optional[int] = None
    chunk: Optional[int] = None
    distance: Optional[float] = None
    excerpt: Optional[str] = None


class QAResponse(BaseModel):
    request_id: str
    answer: str
    sources: List[SourceItem] = []
    latency_ms: int


# ====== 3) App ======
app = FastAPI(title="Gyn KB RAG API", version="0.2.0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/v1/qa", response_model=QAResponse)
def qa(req: QARequest):
    t0 = time.time()
    q = (req.question or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="question is empty")

    request_id = str(int(t0 * 1000))

    try:
        result = run_qa(q, top_k=req.top_k)
        answer = result.get("answer", "")
        sources = result.get("sources", [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    latency_ms = int((time.time() - t0) * 1000)
    return QAResponse(
        request_id=request_id,
        answer=answer,
        sources=sources,
        latency_ms=latency_ms,
    )


@app.post("/v1/qa/stream")
def qa_stream(req: QARequest):
    """
    SSE 流式接口（JSON events）
    - 第一条：sources
    - 后续：chunk
    - 最后：done
    """
    q = (req.question or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="question is empty")

    qa_bot = _load_qa_bot()
    bot = qa_bot._get_bot()  # 复用你 qa_bot.py 的单例（避免重复初始化）

    request_id = str(int(time.time() * 1000))

    def sse(data: Dict[str, Any], event: Optional[str] = None) -> str:
        payload = json.dumps(data, ensure_ascii=False)
        if event:
            return f"event: {event}\ndata: {payload}\n\n"
        return f"data: {payload}\n\n"

    def generate() -> Generator[str, None, None]:
        t0 = time.time()
        try:
            # 1) 先检索，拿 sources + context（不让模型编引用）
            context, sources = bot.retrieve(q, top_k=req.top_k)

            # 先把 sources 发给前端
            yield sse(
                {"type": "sources", "request_id": request_id, "sources": sources},
                event="sources",
            )

            # 2) 再开始流式生成
            user_prompt = (
                f"问题：{q}\n\n"
                f"资料：\n{context}\n\n"
                "请用中文回答，并尽量引用资料中的表述（但不要大段照抄）。"
            )

            stream_resp = chat(
                model=bot.llm_model,
                messages=[
                    {"role": "system", "content": bot.system_prompt_no_refs},
                    {"role": "user", "content": user_prompt},
                ],
                stream=True,
            )

            for chunk in stream_resp:
                content = chunk.get("message", {}).get("content")
                if content:
                    yield sse(
                        {"type": "chunk", "content": content},
                        event="chunk",
                    )

            latency_ms = int((time.time() - t0) * 1000)
            yield sse(
                {"type": "done", "request_id": request_id, "latency_ms": latency_ms},
                event="done",
            )

        except Exception as e:
            yield sse(
                {"type": "error", "request_id": request_id, "message": str(e)},
                event="error",
            )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
