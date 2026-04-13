"""
工具：知识库检索

学习要点：
1. @tool 装饰器 - LangChain 定义工具的标准方式
2. 工具的 name 和 description - Agent 根据这两个字段决定何时调用该工具
3. description 要写清楚"什么时候该用这个工具"，这直接影响 Agent 的决策
"""
from langchain_core.tools import tool
from src.rag.hybrid_search import enhanced_search


@tool
def search_knowledge_base(query: str) -> str:
    """搜索设备知识库，查找设备手册、操作规范、故障案例等技术文档。
    当需要查询设备的技术参数、操作流程、日志规范、错误码含义、
    硬件接口说明等信息时使用此工具。

    Args:
        query: 搜索关键词，例如"制冰机故障"、"日志错误码"、"机械臂接口"
    """
    results = enhanced_search(query, k=5)

    if not results:
        return "知识库中没有找到相关文档。"

    output_parts = []
    for i, (doc, score) in enumerate(results, 1):
        source = doc.metadata.get("filename", "未知来源")
        headers = []
        for key in ["h1", "h2", "h3"]:
            if key in doc.metadata:
                headers.append(doc.metadata[key])
        header_str = " > ".join(headers) if headers else ""

        output_parts.append(
            f"[{i}] 来源: {source}"
            + (f" | 章节: {header_str}" if header_str else "")
            + f"\n{doc.page_content[:500]}"
        )

    return "\n\n---\n\n".join(output_parts)
