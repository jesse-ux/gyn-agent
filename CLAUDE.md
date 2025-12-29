# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **local RAG (Retrieval-Augmented Generation) system** for women's health Q&A. It processes Chinese PDF documents, builds a local vector knowledge base, and provides a web interface for asking questions with citations. The entire system runs locally using Ollama for LLM/Embedding inference.

**Important**: This is a learning project for RAG engineering, NOT a medical diagnosis system.

---

## Architecture Flow

```
PDF Documents
    ↓
[scripts/] Python Processing Pipeline
    ├─ pdf_parser.py      → PyMuPDF text extraction
    ├─ text_splitter.py   → HanLP sentence splitting & chunking
    ├─ embeddings.py      → Qwen3-Embedding via Ollama
    └─ chroma_store.py    → ChromaDB vector storage
    ↓
[services/rag_api/] FastAPI Backend
    ├─ /v1/qa             → Sync Q&A endpoint
    ├─ /v1/qa/stream      → SSE streaming endpoint
    └─ /v1/transcribe     → Whisper speech-to-text with LLM correction
    ↓
[apps/web/] Next.js Frontend (App Router)
    └─ /chat              → Q&A interface with citations + voice input
```

**Key Insight**: The system uses a **smart deduplication** strategy that groups retrieved chunks by (source, page) and keeps only the most similar result before passing to the LLM.

---

## Development Commands

### Backend (Python/FastAPI)

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start backend (auto-reload)
uvicorn services.rag_api.app.main:app --reload --port 8000

# Test endpoints
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/v1/qa \
  -H "Content-Type: application/json" \
  -d '{"question": "测试问题", "top_k": 6}'
```

### Frontend (Next.js)

```bash
cd apps/web
npm install
npm run dev          # Start dev server on http://localhost:3000
```

### Knowledge Base Building

```bash
# 1. Place PDFs in data/pdfs/
# 2. Run indexing
source .venv/bin/activate
python scripts/main.py

# Note: Update scripts/main.py to add more PDFs to the list
```

### Ollama Models

```bash
# Required models
ollama pull dengcao/Qwen3-Embedding-0.6B:Q8_0  # Embedding model
ollama pull Qwen3:0.6B                        # LLM model

# Verify Ollama is running
curl http://localhost:11434/api/tags
```

---

## Configuration

**Main Config**: `scripts/config.py`

Key settings:
- `EMBED_MODEL`: Model name for text vectorization (default: `"dengcao/Qwen3-Embedding-0.6B:Q8_0"`)
- `LLM_MODEL`: Model name for answer generation (default: `"Qwen3:0.6B"`)
- `MAX_CHARS_PER_CHUNK`: 900 chars per chunk
- `OVERLAP_SENTENCES`: 2 sentences overlap between chunks
- `EMBED_BATCH_SIZE`: 32 chunks per batch
- `DEFAULT_TOP_K`: 6 chunks retrieved per query

**Environment Variables**:
- `RAG_API_BASE`: Backend API URL (default: `http://127.0.0.1:8000`)
  - Set in `apps/web/.env.local` to override default

---

## Code Architecture

### Backend: `services/rag_api/app/main.py`

**Key Functions**:
- `run_qa()`: Calls `qa_bot.answer_question_with_sources()` for sync responses
- `run_qa_stream()`: Uses SSE events for streaming responses
- `transcribe_audio()`: Whisper speech-to-text with LLM correction layer

**SSE Event Types** (for streaming):
```python
{
  "sources": [{"type": "sources", "sources": [...]}],
  "chunk": [{"type": "chunk", "content": "text"}],
  "done": [{"type": "done", "latency_ms": 1234}],
  "error": [{"type": "error", "message": "..."}]
}
```

**Audio Transcription Flow**:
1. Whisper (small model) for initial transcription with medical context prompt
2. LLM (qwen3:0.6b) for semantic error correction (homophone fixes like "9架"→"9价")

### RAG Core: `scripts/qa_bot.py`

**Class: QABot**
- `retrieve(question, top_k)`: Main retrieval method with deduplication
  - Returns: `(context_string, sources_list)`
  - Deduplicates by (source, page), keeps lowest distance
- `answer_with_sources()`: Returns `{"answer": str, "sources": list}`
- `answer_stream()`: Generator for streaming responses

**System Prompts**:
- `system_prompt_with_refs`: For CLI/testing, includes reference formatting in response
- `system_prompt_no_refs`: For API, excludes references (handled by backend sources)

**Important**: The `retrieve()` method fetches `top_k * 2` results to ensure enough unique sources after deduplication.

### Frontend: `apps/web/app/chat/page.tsx`

**State Management**:
- `streamLoading`: Streaming in progress
- `showStreamSources`: Controls when to display sources (after completion)
- `streamSources`: Accumulates citation data

**SSE Parsing Logic**:
- Uses buffer to handle split JSON chunks
- Parses `event:` and `data:` lines
- Switches on `type` field (sources/chunk/done/error)

**Audio Input**:
- `AudioRecorder` component (microphone button in textarea)
- Calls `/api/transcribe` which proxies to backend Whisper+LLM pipeline
- Appends transcribed text to question input

---

## Key Implementation Details

### Deduplication Strategy

Located in `qa_bot.py:retrieve()`:
```python
# Groups by (source, page) key
unique_docs: Dict[Tuple[str, Any], Dict] = {}

# Keeps only the lowest distance result
if key not in unique_docs or dist < unique_docs[key]["distance"]:
    unique_docs[key] = {"doc": d, "meta": m, "distance": dist}

# Sorts by distance and takes top_k
sorted_items = sorted(unique_docs.values(), key=lambda x: x["distance"])[:top_k]
```

### Citation Display

Frontend uses circular number badges (①②③) with hover tooltips:
- **Why**: Cleaner UI than showing full citations inline
- **Interaction**: Hover/click to reveal full source details
- **Timing**: Sources appear only after answer completes (streaming mode)

### Streaming vs Sync Mode

| Mode | Endpoint | Use Case |
|------|----------|----------|
| Sync | `/v1/qa` | Batch queries, simple integration |
| Stream | `/v1/qa/stream` | Real-time UX, progressive display |

**Frontend handles both modes** with separate buttons and state management.

### Speech-to-Text Pipeline

Two-layer correction for better accuracy:
1. **Whisper small model**: Initial transcription with medical context prompt
2. **LLM correction**: Fixes homophone errors (e.g., "9架"→"9价", "爱吃皮威"→"HPV")

Common corrections handled in `CORRECTION_SYSTEM_PROMPT`:
- "9架"/"九家" → "9价" (HPV vaccine)
- "垃圾种" → "哪几种"
- "囊种" → "囊肿"
- "极流" → "肌瘤"
- "爱吃皮威" → "HPV"

---

## Common Patterns

### Adding New API Endpoints

1. Add handler in `services/rag_api/app/main.py`
2. Create corresponding proxy in `apps/web/app/api/` (if frontend needs it)
3. Export function from `scripts/qa_bot.py` if needed

### Modifying RAG Pipeline

**Chunking**: Edit `scripts/text_splitter.py` and `scripts/config.py`
**Embedding**: Edit `scripts/embeddings.py`
**Retrieval**: Edit `scripts/qa_bot.py:retrieve()`
**LLM Prompt**: Edit `scripts/qa_bot.py` system prompts

### Frontend State Flow

For streaming responses:
```typescript
setStreamLoading(true)           // Start
  → Receive 'sources' event      // Save to state, don't show yet
  → Receive 'chunk' events       // Append to streamData
  → Receive 'done' event        // setShowStreamSources(true)
setStreamLoading(false)          // End
```

---

## File Import Patterns

**Backend imports** (add to `sys.path` in FastAPI):
```python
PROJECT_ROOT = Path(__file__).resolve().parents[3]  # Up to gyn-agent/
sys.path.insert(0, str(PROJECT_ROOT))
import scripts.qa_bot as qa_bot
```

**Frontend API proxy**:
```typescript
// apps/web/app/api/qa/route.ts
const apiBase = process.env.RAG_API_BASE || "http://127.0.0.1:8000";
await fetch(`${apiBase}/v1/qa`, { ... });
```

---

## Testing

### Backend Testing
```bash
# Direct Python test
python scripts/qa_bot.py  # Has __main__ test block

# API test with curl
curl -X POST http://127.0.0.1:8000/v1/qa/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "测试", "top_k": 3}'
```

### Frontend Testing
```bash
# Start both services
# Backend: port 8000
# Frontend: port 3000
# Navigate to http://localhost:3000/chat
```

---

## Important Notes

- **Data Privacy**: All processing is local; no external API calls for inference
- **Chinese NLP**: HanLP used for sentence splitting (downloads models on first run)
- **Model Compatibility**: Embedding/LLM models should be from same family (Qwen3)
- **Chroma Persistence**: Vector DB stored in `data/chroma/` - persists across runs
- **PDF Copyright**: Keep `data/pdfs/` in `.gitignore`
- **Whisper Model**: Uses "small" model by default (configurable in `main.py`)
