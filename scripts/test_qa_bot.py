"""测试问答机器人模块"""

from qa_bot import QABot
from config import EMBED_MODEL, LLM_MODEL, CHROMA_DIR, COLLECTION_NAME

print("Testing Q&A Bot")
print("="*60)

# 初始化机器人
bot = QABot(
    embed_model=EMBED_MODEL,
    llm_model=LLM_MODEL,
    persist_dir=str(CHROMA_DIR),
    collection_name=COLLECTION_NAME
)

# 显示数据库信息
info = bot.store.get_collection_info()
print(f"\nDatabase info:")
print(f"  Collection: {info['name']}")
print(f"  Documents: {info['count']}")

# 测试问题
test_questions = [
    "什么是细菌性阴道炎？",
    "怀孕期间应该做哪些检查？",
    "宫颈癌的预防方法有哪些？",
]

print("\n" + "="*60)
print("Asking questions...")
print("="*60 + "\n")

for question in test_questions:
    print(f"问题: {question}\n")

    try:
        answer = bot.answer(question, top_k=6)
        print(f"答案:\n{answer}\n")
    except Exception as e:
        print(f"Error: {e}\n")

    print("-" * 60 + "\n")
