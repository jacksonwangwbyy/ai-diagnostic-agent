"""
RAG 检索链 - 将向量检索与 LLM 生成串联起来

学习要点：
1. RAG 核心流程：Query → 检索相关文档 → 拼入 Prompt → LLM 生成回答
2. Prompt 模板设计 - 把检索到的文档作为上下文注入 system prompt
3. 引用溯源 - 回答中标注信息来源，方便用户验证
"""
from langchain_core.documents import Document
from langchain_core.messages import SystemMessage, HumanMessage
from src.rag.vectorstore import search_with_scores
from src.llm.client import create_llm, extract_text


RAG_SYSTEM_PROMPT = """你是 SMYZE 饮吧设备的智能故障诊断助手。

请根据以下检索到的设备文档来回答用户的问题。

## 参考文档

{context}

## 回答要求

1. 优先基于上面的参考文档来回答，如果文档中有相关内容，请引用具体来源
2. 如果文档中没有直接答案，可以结合文档信息和你的知识进行推理
3. 回答要具体可执行，像一个经验丰富的运维工程师在和同事交流
4. 在回答末尾列出引用的文档来源
"""


def format_context(results: list[tuple[Document, float]]) -> str:
    """
    将检索结果格式化为 Prompt 中的上下文文本

    每个文档块包含：来源文件名、相关度分数、内容
    """
    context_parts = []
    for i, (doc, score) in enumerate(results, 1):
        source = doc.metadata.get("filename", "未知来源")
        # 如果有标题层级信息（Markdown 切分产生的），也加上
        headers = []
        for key in ["h1", "h2", "h3"]:
            if key in doc.metadata:
                headers.append(doc.metadata[key])
        header_str = " > ".join(headers) if headers else ""

        context_parts.append(
            f"[文档 {i}] 来源: {source}"
            + (f" | 章节: {header_str}" if header_str else "")
            + f" | 相关度: {score:.3f}"
            + f"\n{doc.page_content}"
        )

    return "\n\n---\n\n".join(context_parts)


def rag_query(question: str, provider: str = None, k: int = 5) -> dict:
    """
    RAG 问答：检索 + 生成

    Args:
        question: 用户问题
        provider: LLM provider（claude/openai）
        k: 检索 top-k 个文档

    Returns:
        dict: {
            "answer": 回答文本,
            "sources": 引用的文档来源列表,
            "context_count": 检索到的文档数量,
        }
    """
    # Step 1: 检索相关文档
    results = search_with_scores(question, k=k)

    if not results:
        return {
            "answer": "知识库中没有找到相关文档，请确认知识库已构建。",
            "sources": [],
            "context_count": 0,
        }

    # Step 2: 格式化上下文
    context = format_context(results)

    # Step 3: 构造 Prompt 并调用 LLM
    llm = create_llm(provider)
    messages = [
        SystemMessage(content=RAG_SYSTEM_PROMPT.format(context=context)),
        HumanMessage(content=question),
    ]

    response = llm.invoke(messages)
    answer = extract_text(response.content)

    # Step 4: 提取引用来源
    sources = list(set(
        doc.metadata.get("filename", "未知") for doc, _ in results
    ))

    return {
        "answer": answer,
        "sources": sources,
        "context_count": len(results),
    }


def rag_stream(question: str, provider: str = None, k: int = 5):
    """
    RAG 流式问答

    Yields:
        每个 token 的文本（流式输出）

    最后 yield 一个 dict 包含元信息（sources 等）
    """
    # Step 1: 检索
    results = search_with_scores(question, k=k)

    if not results:
        yield "知识库中没有找到相关文档。"
        return

    # Step 2: 构造 Prompt
    context = format_context(results)
    llm = create_llm(provider)
    messages = [
        SystemMessage(content=RAG_SYSTEM_PROMPT.format(context=context)),
        HumanMessage(content=question),
    ]

    # Step 3: 流式生成
    for chunk in llm.stream(messages):
        token = chunk.content
        if isinstance(token, str):
            yield token
        elif isinstance(token, list):
            for block in token:
                if isinstance(block, dict) and block.get("type") == "text":
                    yield block["text"]

    # Step 4: 输出来源
    sources = list(set(
        doc.metadata.get("filename", "未知") for doc, _ in results
    ))
    yield f"\n\n---\n📄 参考文档: {', '.join(sources)}"
