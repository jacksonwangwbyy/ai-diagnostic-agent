"""
知识库构建脚本

用法：
    cd "D:/software project/ai-diagnostic-agent"

    # 使用本地 Embedding（离线，不依赖 API）
    .venv/Scripts/python scripts/build_knowledge_base.py --local

    # 使用 OpenAI Embedding（效果更好，需要 API）
    .venv/Scripts/python scripts/build_knowledge_base.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rag.loader import load_directory
from src.rag.splitter import split_documents
from src.rag.vectorstore import create_vector_store


def build(use_local: bool = False):
    print("=" * 50)
    print("📚 知识库构建")
    print("=" * 50)

    # Step 1: 加载文档
    print("\n[1/3] 加载文档...")
    manuals_dir = os.path.join(os.path.dirname(__file__), "..", "knowledge-base", "device-manuals")
    cases_dir = os.path.join(os.path.dirname(__file__), "..", "knowledge-base", "fault-cases")

    documents = []
    if os.path.exists(manuals_dir):
        print(f"\n--- {manuals_dir} ---")
        documents.extend(load_directory(manuals_dir))

    if os.path.exists(cases_dir) and os.listdir(cases_dir):
        print(f"\n--- {cases_dir} ---")
        documents.extend(load_directory(cases_dir))

    if not documents:
        print("没有找到任何文档，请先将文档放入 knowledge-base/ 目录")
        return

    # Step 2: 切分
    print(f"\n[2/3] 切分文档...")
    chunks = split_documents(documents, chunk_size=800, chunk_overlap=150)

    # 打印切分统计
    print(f"\n--- 切分统计 ---")
    source_stats = {}
    for chunk in chunks:
        name = chunk.metadata.get("filename", "unknown")
        source_stats[name] = source_stats.get(name, 0) + 1
    for name, count in sorted(source_stats.items()):
        print(f"  {name}: {count} 块")

    # Step 3: Embedding + 存入 ChromaDB
    print(f"\n[3/3] Embedding 并存入 ChromaDB...")
    vectorstore = create_vector_store(chunks, use_local_embedding=use_local)

    print(f"\n{'=' * 50}")
    print(f"✅ 知识库构建完成！")
    print(f"   文档数: {len(documents)}")
    print(f"   块数: {len(chunks)}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    use_local = "--local" in sys.argv
    build(use_local=use_local)
