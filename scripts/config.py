"""配置文件 - 集中管理所有配置项"""

from pathlib import Path

# 模型配置
EMBED_MODEL = "dengcao/Qwen3-Embedding-0.6B:Q8_0"
LLM_MODEL = "Qwen3:0.6B"

# 路径配置
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
PDF_DIR = DATA_DIR / "pdfs"
CHROMA_DIR = DATA_DIR / "chroma"

# ChromaDB 配置
COLLECTION_NAME = "gyn_kb"

# 文本切分配置
MAX_CHARS_PER_CHUNK = 900
OVERLAP_SENTENCES = 2

# Embedding 批处理配置
EMBED_BATCH_SIZE = 32

# RAG 检索配置
DEFAULT_TOP_K = 6
