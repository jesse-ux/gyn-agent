"""测试 API 接口 - 验证 answer_question 和 qa 函数"""

from qa_bot import answer_question, qa, QABot

print("Testing API Interface")
print("="*60)

# 显示数据库信息
bot = QABot()
info = bot.store.get_collection_info()
print(f"\nDatabase info:")
print(f"  Collection: {info['name']}")
print(f"  Documents: {info['count']}")

if info['count'] == 0:
    print("\n⚠️  警告: 数据库为空！请先运行: python main.py")
    exit(1)

# 测试问题
test_questions = [
    ("什么是细菌性阴道炎？", 6),
    ("怀孕期间应该做哪些检查？", 3),
]

print("\n" + "="*60)
print("Testing answer_question()")
print("="*60 + "\n")

for question, top_k in test_questions:
    print(f"问题 ({top_k} chunks): {question}\n")

    try:
        answer = answer_question(question, top_k=top_k)
        print(f"答案:\n{answer}\n")
    except Exception as e:
        print(f"❌ Error: {e}\n")

    print("-" * 60 + "\n")

print("\n" + "="*60)
print("Testing qa() - shorter function name")
print("="*60 + "\n")

question = "宫颈癌如何预防？"
print(f"问题: {question}\n")

try:
    answer = qa(question, top_k=3)
    print(f"答案:\n{answer}\n")
except Exception as e:
    print(f"❌ Error: {e}\n")

print("\n✅ All tests completed!")
