# gyn-agent

> 基于本地知识库的妇科健康科普问答 RAG 系统

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-green)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14%2B-black)](https://nextjs.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

一个面向**女性用户**的妇科健康科普问答 Agent 练习项目，基于本地 PDF 构建知识库，支持网页端问答与流式输出。

## 🎯 项目目标

> 本项目**不是**医疗诊断系统，而是用于学习 **RAG 工程链路**的实践项目。

**完整流程：**
```
PDF → 清洗 → HanLP切片 → 向量化(Qwen Embedding)
  → Chroma检索 → LLM生成(Qwen) → 结构化引用输出
```

**核心特性：**
- ✅ 输出带"来源（书名/页码）"的可追溯回答
- ✅ 本地部署，数据隐私安全
- ✅ 支持流式/非流式两种问答模式
- ✅ 智能去重，避免重复引用

---

## ✨ 功能特性

### 📚 本地知识库 RAG
- **PDF 解析与清洗** - 提取文本、去除噪音
- **HanLP 智能切片** - 按句/按块切分，支持重叠
- **Ollama 向量化** - 使用 `Qwen-Embedding-0.6B` 生成向量
- **Chroma 持久化** - 本地向量数据库，支持增量更新
- **智能去重** - 按 (来源, 页码) 去重，保留相似度最高的结果

### 💬 双模式问答
- **非流式模式** - 一次性返回完整答案，适合批量查询
- **流式模式** - SSE 逐字输出，提升用户体验
- **结构化引用** - 返回 `sources`（书名/页码/片段/相似度）

### 🎨 友好的前端界面
- **Markdown 渲染** - 美观的答案展示
- **圆形数字标签** - 悬停/点击查看引用详情
- **渐进式显示** - 先显示答案，完成后展示来源
- **实时状态** - 显示生成进度和耗时

---

## 🛠️ 技术栈

| 类别 | 技术 | 版本 |
|------|------|------|
| **前端** | Next.js (App Router) | 14+ |
| **后端** | FastAPI | 0.115+ |
| **向量库** | Chroma | 1.4+ |
| **NLP** | HanLP | 2.1+ |
| **LLM** | Ollama (Qwen) | 0.4+ |

**模型配置：**
```bash
# Embedding 模型
ollama pull qwen3-embedding:0.6b

# LLM 模型（可替换为更大模型）
ollama pull qwen3:0.6b
```

---

## 📁 项目结构

```
gyn-agent/
├── apps/
│   └── web/                    # Next.js 前端
│       └── app/
│           ├── chat/           # 问答页面
│           └── api/qa/         # API 代理层
│
├── services/
│   └── rag_api/                # FastAPI 后端
│       └── app/
│           └── main.py         # API 入口
│
├── scripts/                     # RAG 核心逻辑
│   ├── config.py               # 配置文件
│   ├── pdf_parser.py           # PDF 解析
│   ├── text_splitter.py        # 文本切片
│   ├── embeddings.py           # 向量化
│   ├── chroma_store.py         # 向量库封装
│   └── qa_bot.py               # 问答机器人
│
├── data/
│   ├── chroma/                 # Chroma 持久化目录
│   └── pdfs/                   # PDF 文档（.gitignore）
│
├── requirements.txt            # Python 依赖
└── README.md                   # 项目文档
```

---

## 🚀 快速开始

### 前置要求

- **Python** 3.10+ （建议使用虚拟环境）
- **Node.js** 18+ 或 20+
- **Ollama** 已安装并运行

> ⚠️ **注意**：PDF 文档通常涉及版权，建议将文件放在 `data/pdfs/` 并添加到 `.gitignore`。

### 1️⃣ 安装依赖

**Python 环境：**
```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

**Node.js 环境：**
```bash
cd apps/web
npm install
```

### 2️⃣ 拉取模型

```bash
# Embedding 模型
ollama pull qwen3-embedding:0.6b

# LLM 模型
ollama pull qwen3:0.6b
```

> 💡 如使用其他模型，请修改 `scripts/config.py` 中的配置。

### 3️⃣ 构建知识库

```bash
# 将 PDF 文档放入 data/pdfs/ 目录

# 运行索引脚本
source .venv/bin/activate
python scripts/generate_index.py
```

索引完成后，向量数据会保存到 `data/chroma/`。

### 4️⃣ 启动后端服务

```bash
source .venv/bin/activate
uvicorn services.rag_api.app.main:app --reload --port 8000
```

**服务地址：**
- 健康检查：http://127.0.0.1:8000/health
- API 文档：http://127.0.0.1:8000/docs

### 5️⃣ 启动前端

```bash
cd apps/web
npm run dev
```

**访问地址：**
- 问答页面：http://localhost:3000/chat

---

## 📡 API 接口

### 非流式问答

**端点：** `POST /v1/qa`

**请求示例：**
```json
{
  "question": "宫颈癌的预防方法有哪些？",
  "top_k": 6
}
```

**响应示例：**
```json
{
  "request_id": "1735147369000",
  "answer": "宫颈癌的预防方法包括：\n1. HPV 疫苗接种...",
  "sources": [
    {
      "rank": 1,
      "source": "妇产科学.pdf",
      "page": 338,
      "chunk": 0,
      "distance": 0.12,
      "excerpt": "宫颈癌的预防措施包括疫苗接种..."
    }
  ],
  "latency_ms": 1234
}
```

**字段说明：**
- `sources` 已按 (来源, 页码) 去重
- `distance` 越小表示相似度越高
- `excerpt` 为文档片段摘要（前 220 字）

---

### 流式问答 (SSE)

**端点：** `POST /v1/qa/stream`

**请求示例：**
```json
{
  "question": "没按时来月经怎么办？",
  "top_k": 6
}
```

**SSE 事件流：**
```
event: sources
data: {"type": "sources", "request_id": "123", "sources": [...]}

event: chunk
data: {"type": "chunk", "content": "月经"}

event: chunk
data: {"type": "chunk", "content": "不规律"}

...

event: done
data: {"type": "done", "request_id": "123", "latency_ms": 5678}
```

**事件类型：**

| 事件 | 说明 | 字段 |
|------|------|------|
| `sources` | 参考来源（先发送） | `sources[]` |
| `chunk` | 文本片段（逐字） | `content` |
| `done` | 完成标记 | `latency_ms` |
| `error` | 错误信息 | `message` |

**前端处理建议：**
1. 接收 `sources` 后缓存，等答案完成后再显示
2. 累积 `chunk.content` 逐字渲染
3. 收到 `done` 后显示参考来源并停止加载

---

## ⚖️ 免责声明

本项目用于**学习与工程实践**：

- ✅ 提供妇科健康科普信息整理
- ❌ 不进行医疗诊断
- ❌ 不提供处方或药物剂量建议

> 若涉及紧急/高风险情况，请**及时就医或急诊**。

内容来源于本地 PDF 资料，若资料不足会提示"资料不足以回答"。

---

## 🛣️ 开发路线图

### 🎯 Agent 能力增强
- [ ] **Safety Router** - 对"求诊断/求用药"等问题做分流与强提醒
- [ ] **Skills 系统** - 检索、总结、风险提示、引用整理等可组合能力
- [ ] **Prompt Engineering** - 提升答案结构一致性和引用准确性
- [ ] **评测集** - 构建 50~200 条问题集，评估召回率/准确率

### 🎤 语音交互
- [ ] 语音输入（STT）- 接入 Whisper / faster-whisper
- [ ] 语音输出（TTS）- 实现语音问答
- [ ] 前端录音按钮 + 播放器

### 🔌 MCP & 工具调用
- [ ] 接入 MCP 工具（检索、摘要、结构化输出）
- [ ] 设计工具协议与权限边界

### 🐳 容器化与平台化
- [ ] Docker Compose 一键启动（web + api + ollama + chroma）
- [ ] LangChain 集成
- [ ] Dify 工作流编排

---

## 🤝 贡献指南

欢迎提 Issue / Pull Request！

**特别欢迎贡献的领域：**
- 切片策略优化
- 检索召回效果提升
- 引用展示优化
- Prompt 安全边界
- 语音交互实现

---

## 📄 开源协议

[MIT License](LICENSE)

---

<div align="center">

**Made with ❤️ for learning RAG & Agent Engineering**

[⬆ 返回顶部](#gyn-agent)

</div>
