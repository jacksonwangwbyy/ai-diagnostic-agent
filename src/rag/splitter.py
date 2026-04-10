"""
文本切分器 - 将长文档切分为适合 Embedding 的小块

学习要点：
1. 为什么要切分 - LLM 上下文有限，Embedding 对短文本效果更好
2. chunk_size - 每个块的最大字符数，太大检索不精确，太小丢失上下文
3. chunk_overlap - 相邻块的重叠字符数，避免在切分边界丢失语义
4. 切分策略选择 - 按字符、按 Markdown 标题、按语义等
"""
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    MarkdownHeaderTextSplitter,
)
from langchain_core.documents import Document


def create_text_splitter(chunk_size: int = 1000, chunk_overlap: int = 200):
    """
    创建递归字符切分器（通用）

    RecursiveCharacterTextSplitter 会优先按 \n\n, \n, 空格 等分隔符切分，
    尽量保持段落和句子的完整性。

    Args:
        chunk_size: 每个块的最大字符数（建议 500-1500）
        chunk_overlap: 相邻块重叠字符数（建议 chunk_size 的 10%-20%）
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "；", " ", ""],
        length_function=len,
    )


def create_markdown_splitter():
    """
    创建 Markdown 标题切分器

    按 Markdown 标题层级切分，每个 section 是一个独立块。
    标题信息会被添加到 metadata 中，方便检索时知道属于哪个章节。
    """
    return MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "h1"),
            ("##", "h2"),
            ("###", "h3"),
        ]
    )


def split_documents(
    documents: list[Document],
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[Document]:
    """
    切分文档列表

    对 Markdown 文件：先按标题切分，再按字符切分（二次切分）
    对其他文件：直接按字符切分

    Args:
        documents: 原始文档列表
        chunk_size: 块大小
        chunk_overlap: 重叠大小

    Returns:
        切分后的文档列表
    """
    text_splitter = create_text_splitter(chunk_size, chunk_overlap)
    md_splitter = create_markdown_splitter()

    all_chunks = []

    for doc in documents:
        if doc.metadata.get("file_type") == "markdown":
            # Markdown: 先按标题切分
            md_chunks = md_splitter.split_text(doc.page_content)

            # 把标题 metadata 合并到原始 metadata
            for md_chunk in md_chunks:
                md_chunk.metadata.update(doc.metadata)

            # 再按字符切分（处理过长的 section）
            final_chunks = text_splitter.split_documents(md_chunks)
            all_chunks.extend(final_chunks)
        else:
            # 非 Markdown: 直接按字符切分
            chunks = text_splitter.split_documents([doc])
            all_chunks.extend(chunks)

    print(f"切分完成: {len(documents)} 个文档 → {len(all_chunks)} 个块")
    print(f"配置: chunk_size={chunk_size}, chunk_overlap={chunk_overlap}")
    return all_chunks
