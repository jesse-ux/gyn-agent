"""文本切分模块 - 使用 HanLP 进行分句和 chunk 切分"""

from typing import List
import hanlp


# 初始化 HanLP 分句器（懒加载）
_split_sent = None


def get_splitter():
    """获取 HanLP 分句器单例"""
    global _split_sent
    if _split_sent is None:
        print("Loading HanLP sentence splitter...")
        _split_sent = hanlp.load(hanlp.pretrained.eos.UD_CTB_EOS_MUL)
        print("HanLP loaded!")
    return _split_sent


def split_sentences(text: str) -> List[str]:
    """
    使用 HanLP 进行中文分句

    Args:
        text: 输入文本

    Returns:
        句子列表
    """
    splitter = get_splitter()
    return splitter.predict(text)


def chunk_by_sentences(
    sentences: List[str],
    max_chars: int = 900,
    overlap_sents: int = 2
) -> List[str]:
    """
    按句子拼接成固定长度的 chunk（带重叠）

    Args:
        sentences: 句子列表
        max_chars: 每个 chunk 的最大字符数
        overlap_sents: 相邻 chunk 之间的重叠句子数

    Returns:
        chunk 文本列表
    """
    chunks = []
    buf: List[str] = []
    buf_len = 0

    for s in sentences:
        s = s.strip()
        if not s:
            continue

        # 单句超长时单独成块
        if len(s) > max_chars:
            if buf:
                chunks.append("".join(buf).strip())
                buf, buf_len = [], 0
            chunks.append((s + "\n").strip())
            continue

        if buf and (buf_len + len(s) > max_chars):
            chunks.append("".join(buf).strip())
            # 保留最后几句作为重叠
            buf = buf[-overlap_sents:] if overlap_sents > 0 else []
            buf_len = sum(len(x) for x in buf)

        buf.append(s + "\n")
        buf_len += len(s)

    if buf:
        chunks.append("".join(buf).strip())

    return chunks


if __name__ == "__main__":
    # 测试代码
    test_text = """
    妇产科学是临床医学的重要分支。它研究女性生殖系统的生理和病理变化。
    这门学科涵盖了妇科和产科两大领域。妇科主要关注非妊娠期的女性生殖系统疾病。
    产科则专注于妊娠、分娩和产褥期的医疗护理。妇产科医生需要掌握丰富的专业知识。
    """

    sentences = split_sentences(test_text)
    print(f"分句结果（{len(sentences)} 句）：")
    for i, s in enumerate(sentences, 1):
        print(f"  {i}. {s}")

    chunks = chunk_by_sentences(sentences, max_chars=50, overlap_sents=1)
    print(f"\n切分为 {len(chunks)} 个 chunk：")
    for i, c in enumerate(chunks, 1):
        print(f"\nChunk {i} ({len(c)} 字符):")
        print(f"  {c[:100]}...")
