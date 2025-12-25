# Scripts - 模块化脚本说明

## 📁 文件结构

```
scripts/
├── config.py              # 配置文件
├── pdf_parser.py          # PDF 解析模块
├── text_splitter.py       # 文本切分模块
├── embeddings.py          # Embedding 生成模块
├── chroma_store.py        # ChromaDB 存储模块
├── qa_bot.py              # 问答机器人模块
├── main.py                # 主入口（完整流程）
├── test_pdf_parser.py     # PDF 解析测试
├── test_text_splitter.py  # 文本切分测试
├── test_embeddings.py     # Embedding 测试
├── test_qa_bot.py         # 问答机器人测试
└── generate_index.py      # 旧版本（已弃用）
```

## 🚀 使用方式

### 方式 1: 完整流程（一键运行）

```bash
python main.py
```

这会执行完整的 RAG 流程：
1. 解析 PDF
2. 分句和切分
3. 生成 embeddings
4. 存入 ChromaDB
5. 测试问答

### 方式 2: 分步调试

#### 步骤 1: 测试 PDF 解析

```bash
python test_pdf_parser.py
```

**预期输出：**
- 总页数
- 第 1 页的原文和清理后的文本

#### 步骤 2: 测试文本切分

```bash
python test_text_splitter.py
```

**预期输出：**
- 分句结果
- 切分的 chunks 数量和内容

#### 步骤 3: 测试 Embedding 生成

```bash
python test_embeddings.py
```

**预期输出：**
- 向量维度
- 生成时间
- 批量生成性能

#### 步骤 4: 测试完整问答

```bash
python test_qa_bot.py
```

**前提条件：** 需要先运行 `main.py` 建立索引

**预期输出：**
- 数据库文档数量
- 多个问题的回答

## 🔧 模块说明

### config.py

集中管理所有配置：
- 模型名称
- 路径配置
- 参数配置

修改此文件可以调整所有模块的行为。

### pdf_parser.py

**功能：**
- 提取 PDF 每一页的文本
- 清理文本（去除多余空行、特殊字符）

**依赖：** PyMuPDF (fitz)

### text_splitter.py

**功能：**
- 使用 HanLP 进行中文分句
- 按字符长度切分成 chunks（带重叠）

**依赖：** hanlp

**首次运行：** 会自动下载 HanLP 模型（约 100MB）

### embeddings.py

**功能：**
- 调用 Ollama 生成文本向量
- 支持批量处理（提高效率）
- 显示进度条

**依赖：** ollama, tqdm

### chroma_store.py

**功能：**
- 封装 ChromaDB 操作
- 添加/检索文档
- 查询集合信息

**依赖：** chromadb

### qa_bot.py

**功能：**
- 实现完整的 RAG 问答流程
- 检索相关文档
- 调用 LLM 生成答案

**依赖：** ollama, embeddings.py, chroma_store.py

## 📊 调试技巧

### 查看进程状态

```bash
# 查看 Ollama 是否运行
ps aux | grep ollama

# 查看 Python 进程
ps aux | grep python

# 监控 CPU/内存
top -pid $(pgrep ollama)
```

### 查看日志

```bash
# Ollama 日志
tail -f ~/.ollama/logs/server.log

# 查看已加载的模型
curl http://localhost:11434/api/tags
```

### 检查数据库

```bash
# 查看 ChromaDB 数据目录
ls -lh ../data/chroma/

# 检查数据是否增长
watch -n 2 'du -sh ../data/chroma/'
```

## 🐛 常见问题

### 1. HanLP 模型下载慢

**解决：** 使用国内镜像或手动下载模型

### 2. Ollama 连接失败

**检查：**
```bash
curl http://localhost:11434/api/tags
```

**启动 Ollama：**
```bash
ollama serve
```

### 3. 向量生成太慢

**优化：**
- 减小 `EMBED_BATCH_SIZE`
- 使用更小的模型（如 Q8_0 → Q4_0）
- 使用 GPU 加速

### 4. 内存不足

**解决：**
- 减小 `MAX_CHARS_PER_CHUNK`
- 减小 `EMBED_BATCH_SIZE`
- 分批处理 PDF

## 📝 扩展建议

### 添加新的 PDF

在 `main.py` 中修改：
```python
pdf_files = [
    PDF_DIR / "妇产科学.pdf",
    PDF_DIR / "新文档.pdf",  # 添加新文档
]
```

### 修改 chunk 大小

在 `config.py` 中修改：
```python
MAX_CHARS_PER_CHUNK = 500  # 改为 500 字符
```

### 切换模型

在 `config.py` 中修改：
```python
EMBED_MODEL = "nomic-embed-text"  # 使用其他模型
LLM_MODEL = "llama2"              # 使用其他 LLM
```

## 🎯 下一步

- [ ] 添加更多测试问题
- [ ] 支持多轮对话
- [ ] 添加引用来源的高亮显示
- [ ] 实现流式输出（stream）
- [ ] 添加 Web 界面
