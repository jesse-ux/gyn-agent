# services/rag_api/app/main.py
from __future__ import annotations
from fastapi.datastructures import UploadFile

import json
import sys
import time
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

import whisper

from fastapi import FastAPI, HTTPException, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from ollama import chat  # 用于流式时直接 chat（避免重复检索时也可用）


CORRECTION_SYSTEM_PROMPT = """
你是一个专业的医疗听写纠错员。
用户会提供一段语音转录文本，其中可能包含因发音相似导致的错误。
你的任务是利用妇科医疗上下文修正这些错误。

常见修正规则：
1. "9架"、"九家" -> "9价" (指疫苗)
2. "垃圾种" -> "哪几种"
3. "囊种" -> "囊肿"
4. "极流" -> "肌瘤"
5. "爱吃皮威" -> "HPV"

要求：
- 仅输出修正后的文本。
- 不要包含任何解释、前缀或后缀。
- 如果原句没有明显逻辑错误，请原样输出。
"""



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


# --- 初始化 Whisper ---
# 使用 tiny 模型，加载到CPU中
# tiny 模型不是很好用，切换成base试试
print("正在加载 Whisper small 模型...")
try:
    audio_model = whisper.load_model("small")
    print("Whisper small 模型加载成功")
except Exception as e:
    print(f"Whisper small 模型加载失败: {e}")
    audio_model = None


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


# ====== 4) 新增：语音转文字接口 ======
@app.post("/v1/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    if audio_model is None:
        raise HTTPException(status_code=500, detail="Whisper model not initialized")

    if not file.filename.endswith(('.wav', '.mp3', '.m4a', '.webm')):
        raise HTTPException(status_code=400, detail="Invalid file format")

    tmp_path = ""
    try:
        # 1. 保存临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # 2. Whisper 转录 (第一层保障)
        # 即使要在 LLM 纠错，给 Whisper 一个好的提示词也能减少 LLM 的工作量
        whisper_prompt = "妇科问诊。关键词：HPV疫苗、9价、4价、二价、哪几种、预防、感染、子宫肌瘤、卵巢囊肿。"
        
        # 在 Mac 上跑，建议用 base 或 small，fp16=False
        result = audio_model.transcribe(
            tmp_path, 
            language="zh", 
            initial_prompt=whisper_prompt,
            fp16=False 
        )
        
        raw_text = result["text"].strip()
        print(f"1. Whisper 原始结果: {raw_text}")

        # 3. LLM 语义纠错 (第二层保障)
        # 如果 0.6b 效果不好，这里是瓶颈，换 3090 后可以直接上 7B/14B
        corrected_text = raw_text # 默认回退
        
        try:
            response = chat(
                model="qwen3:0.6b", # ❗确保这里是你 ollama list 里有的模型
                messages=[
                    {"role": "system", "content": CORRECTION_SYSTEM_PROMPT},
                    {"role": "user", "content": raw_text},
                ],
                options={"temperature": 0.1} # 低温度，让它更严谨，不要发散
            )
            
            if response.get('message', {}).get('content'):
                corrected_text = response['message']['content'].strip()
                print(f"2. LLM 修正后结果: {corrected_text}")
            else:
                print("LLM 返回为空，使用原始文本")
                
        except Exception as llm_e:
            print(f"LLM 纠错调用失败: {llm_e}")

        # 4. 清理
        os.unlink(tmp_path)

        return {"text": corrected_text}

    except Exception as e:
        print(f"Transcribe error: {e}")
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail=str(e))